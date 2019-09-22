"""Functions for importing and reading ESP-r files"""
from collections import Counter
from datetime import datetime
from itertools import accumulate
import math

import numpy as np
import vtk

from espy.utils import split_to_float, space_data_to_list

# pylint: disable-msg=C0103
# pylint: disable=no-member


def vtk_view(actors, edge_actors, outlines):
    """VTK visualisation setup and render"""

    # Setup camera and specify a particular viewpoint
    camera = vtk.vtkCamera()
    camera.SetFocalPoint(0, 0, 0)
    camera.SetPosition(-100.0, -100.0, 100.0)
    camera.SetViewUp(3.9, 3.4, 1.5)
    camera.SetViewAngle(4.5)

    # Create a renderer, render window, and interactor
    renderer = vtk.vtkRenderer()
    renderer.SetActiveCamera(camera)

    renderWindow = vtk.vtkRenderWindow()
    renderWindow.AddRenderer(renderer)
    renderWindowInteractor = vtk.vtkRenderWindowInteractor()
    renderWindowInteractor.SetRenderWindow(renderWindow)

    # Add the actors to the scene
    for actor, edge_actor, outline in zip(actors, edge_actors, outlines):
        renderer.AddActor(actor)
        renderer.AddActor(edge_actor)
        renderer.AddActor(outline)
    renderer.SetBackground(1, 1, 1)  # white bg

    # Render and interact
    renderWindow.Render()
    renderWindowInteractor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()
    renderWindowInteractor.Start()


def generate_vtk_actors(surf_obj, outer_colour, show_edges=False, show_outline=True):
    """Generates 3 VTK actors.

    Returns 3 VTK actors, which represents an object (geometry & properties) in a rendered scene

    Args:
        surf_obj (vtkObject): vtk Object that defines the surface
        outer_colour (list): Colour and opacity of surface i.e. ["#f5f2d0", 1]

    Returns:
        surface_actor (vtkOpenGLActor): 2D component surface projected on 3D plane
        edge_actor (vtkOpenGLActor): Mesh of surface
        outline_actor (vtkOpenGLActor): Boundary outline of surface

    """
    colors = vtk.vtkNamedColors()

    # Create a mapper and actor
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(surf_obj.GetOutputPort())
    surface_actor = vtk.vtkActor()
    surface_actor.SetMapper(mapper)

    # Get outline of surface
    outline = vtk.vtkFeatureEdges()
    outline.SetInputConnection(surf_obj.GetOutputPort())

    # Get triangulation (mesh) of surface
    extract = vtk.vtkExtractEdges()
    extract.SetInputConnection(surf_obj.GetOutputPort())

    # Define format of surface
    surface_actor.GetProperty().SetColor([x / 255 for x in colors.HTMLColorToRGB(outer_colour[0])])
    surface_actor.GetProperty().SetOpacity(outer_colour[1])

    # Remove lighting, reflections etc.
    surface_actor.GetProperty().SetAmbient(1.0)
    surface_actor.GetProperty().SetDiffuse(0.0)
    surface_actor.GetProperty().SetSpecular(0.0)

    # Define format of mesh
    if show_edges:
        tubes = vtk.vtkTubeFilter()
        tubes.SetInputConnection(extract.GetOutputPort())
        tubes.SetRadius(0.02)
        tubes.SetNumberOfSides(6)
        mapEdges = vtk.vtkPolyDataMapper()
        mapEdges.SetInputConnection(tubes.GetOutputPort())
        edge_actor = vtk.vtkActor()
        edge_actor.SetMapper(mapEdges)
        edge_actor.GetProperty().SetColor(0, 0.643, 0.706)
        edge_actor.GetProperty().SetSpecularColor(1, 1, 1)
        edge_actor.GetProperty().SetSpecular(0.3)
        edge_actor.GetProperty().SetSpecularPower(20)
        edge_actor.GetProperty().SetAmbient(0.2)
        edge_actor.GetProperty().SetDiffuse(0.8)
    else:
        edge_actor = None

    # Define format of outline
    if show_outline:
        outline.SetFeatureEdges(False)
        # ManifoldEdgesOff, NonManifoldEdgesOff, BoundaryEdgesOn
        outline.ColoringOff()
        outline_tubes = vtk.vtkTubeFilter()
        outline_tubes.SetInputConnection(outline.GetOutputPort())
        outline_tubes.SetRadius(0.02)
        outline_tubes.SetNumberOfSides(6)
        outline_mapEdges = vtk.vtkPolyDataMapper()
        outline_mapEdges.SetInputConnection(outline_tubes.GetOutputPort())
        outline_actor = vtk.vtkActor()
        outline_actor.SetMapper(outline_mapEdges)
        outline_actor.GetProperty().SetColor(0, 0, 0)
        outline_actor.GetProperty().SetSpecularColor(1, 1, 1)
        outline_actor.GetProperty().SetSpecular(0.3)
        outline_actor.GetProperty().SetSpecularPower(20)
        outline_actor.GetProperty().SetAmbient(0.2)
        outline_actor.GetProperty().SetDiffuse(0.8)
    else:
        outline_actor = None

    return surface_actor, edge_actor, outline_actor


class Component:
    """Class defining zone component."""

    def __init__(self, property_list, vertices_surf):
        self.name = property_list[0]
        self.position = property_list[1]
        if property_list[2] != "-":
            self.child = property_list[2]
        else:
            self.child = None
        self.usage = []
        if property_list[3] != "-":
            self.usage.append(property_list[3])
            self.usage.append(property_list[4])
        else:
            self.usage = None
        self.construction = property_list[5]
        self.optical_type = property_list[6]
        self.boundary = []
        self.boundary.append(property_list[7])
        self.boundary.append(property_list[8])
        self.boundary.append(property_list[9])
        self.vertices_surf = vertices_surf


    def generate_vtk_surface(self):
        """Generate building component surface as a VTK objects"""
        # Check for duplicate vertices
        dups = [k for k, v in Counter(tuple(x) for x in self.vertices_surf).items() if v > 1]
        if not dups:
            # Normal surface without holes

            # Setup points
            points = vtk.vtkPoints()
            for vertex in self.vertices_surf:
                points.InsertNextPoint(vertex[0], vertex[1], vertex[2])

            # Create the polygon
            polygon = vtk.vtkPolygon()
            polygon.GetPointIds().SetNumberOfIds(len(self.vertices_surf))  # make a polygon
            for i, _ in enumerate(self.vertices_surf):
                polygon.GetPointIds().SetId(i, i)

            # Add the polygon to a list of polygons
            polygons = vtk.vtkCellArray()
            polygons.InsertNextCell(polygon)

            # Create a PolyData
            polygonPolyData = vtk.vtkPolyData()
            polygonPolyData.SetPoints(points)
            polygonPolyData.SetPolys(polygons)

            # Filter the polydata for concave polygons
            surf_obj = vtk.vtkTriangleFilter()
            surf_obj.SetInputData(polygonPolyData)
        else:
            # Assume surface is a 'weakly simple polygon' due to duplicate vertices
            # get indices of duplicates [O(n^2) solution...]
            d = [i for i, x in enumerate(self.vertices_surf) if self.vertices_surf.count(x) > 1]
            # print(d)
            # split into 2 polygons (or len(d)/4 polygons...)
            # vertices_surf_outer = self.vertices_surf[: d[1]] + self.vertices_surf[d[3] + 1 :]
            vertices_surf_outer = self.vertices_surf[: d[0] + 1] + self.vertices_surf[d[-1] + 1 :]
            # vertices_surf_inner = self.vertices_surf[d[1] : d[2]]
            vertices_surf_inner = self.vertices_surf[d[1] : d[2] + 1] + [self.vertices_surf[d[6] - 1]]
            vertices_surf_inner2 = self.vertices_surf[d[3] : d[4]]
            print(vertices_surf_outer)
            print(vertices_surf_inner)

            # Figure out if surface is reversed
            # If the normal of the outer polygon points in a negative direction
            # then the polygons need to be reversed to draw in the correct order
            # print(self.name)
            print(calculate_normal(vertices_surf_outer))
            print(calculate_normal(vertices_surf_inner))
            print(calculate_normal(vertices_surf_inner2))
            if any(t < 0 for t in calculate_normal(vertices_surf_outer)):
                vertices_surf_outer.reverse()
                vertices_surf_inner.reverse()
                vertices_surf_inner2.reverse()

            # Setup points
            points = vtk.vtkPoints()
            for i, vertex in enumerate(vertices_surf_outer):
                points.InsertPoint(i, vertex[0], vertex[1], vertex[2])
            for i, vertex in enumerate(vertices_surf_inner):
                points.InsertPoint(i + len(vertices_surf_outer), vertex[0], vertex[1], vertex[2])
            for i, vertex in enumerate(vertices_surf_inner2):
                points.InsertPoint(i + len(vertices_surf_outer) + len(vertices_surf_inner), vertex[0], vertex[1], vertex[2])

            # Setup polygons
            polys = vtk.vtkCellArray()
            polys.InsertNextCell(len(vertices_surf_outer))
            for i, vertex in enumerate(vertices_surf_outer):
                polys.InsertCellPoint(i)
            polys.InsertNextCell(len(vertices_surf_inner))
            for i, vertex in enumerate(vertices_surf_inner):
                polys.InsertCellPoint(i + len(vertices_surf_outer))
            polys.InsertNextCell(len(vertices_surf_inner2))
            for i, vertex in enumerate(vertices_surf_inner2):
                polys.InsertCellPoint(i + len(vertices_surf_outer) + len(vertices_surf_inner))

            polyData = vtk.vtkPolyData()
            polyData.SetPoints(points)
            polyData.SetPolys(polys)

            # Notice this trick. The SetInput() method accepts a vtkPolyData that
            # is also the input to the Delaunay filter. The points of the
            # vtkPolyData are used to generate the triangulation; the polygons are
            # used to create a constraint region. The polygons are very carefully
            # created and ordered in the right direction to indicate inside and
            # outside of the polygon.
            surf_obj = vtk.vtkDelaunay2D()

            # The input to the Delaunay2D filter is a list of points specified in 3D
            # even though the triangulation is 2D.
            # Thus the triangulation is constructed in the x-y plane, and the z coordinate
            #  is ignored (although carried through to the output).
            # Need to compute the best-fitting plane to the set of points, project the points
            # and that plane and then perform the triangulation using their projected positions
            # and then use it as the plane in which the triangulation is performed.
            # Look into vtkContourTriangulator as well.

            surf_obj.SetInputData(polyData)
            surf_obj.SetSourceData(polyData)
            surf_obj.SetProjectionPlaneMode(vtk.VTK_BEST_FITTING_PLANE)

        return surf_obj


    def set_outer_colour(self):
        """Set default colour of otherside surface based on boundary conditions.
        """
        default_colours = {
            "OPAQUE_ANOTHER": ["#F8F4FF", 1],
            "OPAQUE_ANOTHER_DOOR": ["#f5f2d0", 1],
            "OPAQUE_ANOTHER_PARTN": ["#F8F4FF", 1],
            "OPAQUE_ANOTHER_GRILL": ["#c19a6b", 1],
            "OPAQUE_EXTERIOR": ["#afacac", 1],
            "OPAQUE_EXTERIOR_WALL": ["#afacac", 1],
            "OPAQUE_EXTERIOR_ROOF": ["#afacac", 1],
            "OPAQUE_EXTERIOR_DOOR": ["#c19a6b", 1],
            "OPAQUE_EXTERIOR_FRAME": ["#c19a6b", 1],
            "OPAQUE_EXTERIOR_GRILL": ["#c19a6b", 1],
            "TRANSP_EXTERIOR_WINDOW": ["#008db0", 0.2],
            "OPAQUE_GROUND": ["#654321", 1],
            "OPAQUE_SIMILAR": ["#d8e4bc", 1],
            "OPAQUE_SIMILAR_DOOR": ["#f5f2d0", 1],
            "OPAQUE_SIMILAR_GRILL": ["#c19a6b", 1],
            "OPAQUE_SIMILAR_PARTN": ["#d8e4bc", 1],
            "TRANSP_SIMILAR": [" #0000FF", 0.2],
            "TRANSP_ANOTHER_FICT": [" #0000FF", 0.2],
            "TRANSP_ANOTHER_WINDOW": [" #008db0", 0.2],
        }

        # Get optical _type_
        if self.optical_type == "OPAQUE":
            optics = "OPAQUE"
        else:
            optics = "TRANSP"

        # Construct name for outer surface type
        if self.usage:
            if "WINDOW" in self.usage[0]:
                general_usage = "WINDOW"
            elif "FRAME" in self.usage[0]:
                general_usage = "FRAME"
            elif "DOOR" in self.usage[0]:
                general_usage = "DOOR"
            else:
                general_usage = self.usage[0]
            boundary_type = "_".join([optics, self.boundary[0], general_usage])
        else:
            boundary_type = "_".join([optics, self.boundary[0]])

        # Lookup name in colour dictionary
        # default to red if not available in default colour dictionary
        surf_colour = default_colours.get(boundary_type)
        if surf_colour is None:
            print(
                "Unable to find default colour for component {} of type {}.".format(
                    self.name, boundary_type
                ),
                end="",
            )
            print(" Setting default colour to red.")
            surf_colour = ["#ff0000", 1]

        return surf_colour


def calculate_normal(p):
    """
    Newell's method for calculating the normal of an arbitrary 3D polygon.
    """
    normal = [0, 0, 0]
    for i, _ in enumerate(p):
        j = (i + 1) % len(p)
        normal[0] += (p[i][1] - p[j][1]) * (p[i][2] + p[j][2])
        normal[1] += (p[i][2] - p[j][2]) * (p[i][0] + p[j][0])
        normal[2] += (p[i][0] - p[j][0]) * (p[i][1] + p[j][1])
    # normalise
    nn = [0, 0, 0]
    nn[0] = normal[0] / math.sqrt((normal[0])**2 + (normal[1])**2 + (normal[2])**2)
    nn[1] = normal[1] / math.sqrt((normal[0])**2 + (normal[1])**2 + (normal[2])**2)
    nn[2] = normal[2] / math.sqrt((normal[0])**2 + (normal[1])**2 + (normal[2])**2)
    return nn


def area(poly):
    """area of polygon poly
    Source: https://stackoverflow.com/a/12643315
    Source 2: http://geomalgorithms.com/a01-_area.html#3D%20Polygons
    TODO(j.allison): this function should probably live in a different module
    """

    def cross(a, b):
        """cross product of vectors a and b."""
        x = a[1] * b[2] - a[2] * b[1]
        y = a[2] * b[0] - a[0] * b[2]
        z = a[0] * b[1] - a[1] * b[0]
        return (x, y, z)

    if len(poly) < 3:  # not a plane - no area
        return 0

    total = [0, 0, 0]
    for i, _ in enumerate(poly):
        vi1 = poly[i]
        if i is len(poly) - 1:
            vi2 = poly[0]
        else:
            vi2 = poly[i + 1]
        prod = cross(vi1, vi2)
        total[0] += prod[0]
        total[1] += prod[1]
        total[2] += prod[2]
    result = np.linalg.norm(total)
    return round(result / 2, 3)


def _read_file(filepath):
    """
    Reads in generic ESP-r format files.
    All comments (#) are stripped and each line is an element in the returned
    list. Each line element is stripped of whitespace at either end, and is
    partitioned at the first whitespace character.
    Further splitting of elements will be required based on what file type is
    being read.
    """
    file = []
    with open(filepath, "r") as fp:
        for line in fp:
            # .partition returns a tuple: everything before the partition string,
            # the partition string, and everything after the partition string.
            # By indexing with [0] takes just the part before the partition string.
            line = line.partition("#")[0]

            # Split line after first whitespace and remove all whitespace
            line = [x.strip() for x in line.strip().split(" ", 1)]

            # if line not empty append to file list
            if line[0]:
                file.append(line)
    return file


def _get_var(ifile, find_str):
    y = [x[1] for x in ifile if x[0] == find_str]
    if y:
        var = y[0]
    else:
        var = None

    return var


def config(filepath):
    """
    Reads in an ESP-r configuration file.
    """
    cfg = _read_file(filepath)

    # Modified date
    date = _get_var(cfg, "*date")  # string
    date = datetime.strptime(date, "%a %b %d %H:%M:%S %Y")  # datetime

    # Build dictionary of model paths
    paths = {
        "zones": _get_var(cfg, "*zonpth"),
        "networks": _get_var(cfg, "*netpth"),
        "controls": _get_var(cfg, "*ctlpth"),
        "aim": _get_var(cfg, "*aimpth"),
        "radiance": _get_var(cfg, "*radpth"),
        "images": _get_var(cfg, "*imgpth"),
        "documents": _get_var(cfg, "*docpth"),
        "databases": _get_var(cfg, "*dbspth"),
        "hvac": _get_var(cfg, "*hvacpth"),
        "BASESIMP": _get_var(cfg, "*bsmpth"),
    }

    # Build dictionary of model databases
    # TODO(j.allison): If non-standard db, gets different name
    # should pull into a single db
    databases = {
        "std_material": _get_var(cfg, "*stdmat"),
        "material": _get_var(cfg, "*mat"),
        "cfc": _get_var(cfg, "*stdcfcdb"),
        "std_mlc": _get_var(cfg, "*stdmlc"),
        "mlc": _get_var(cfg, "*mlc"),
        "optics": _get_var(cfg, "*stdopt"),
        "pressure": _get_var(cfg, "*stdprs"),
        "devn": _get_var(cfg, "*stdevn"),
        "climate": _get_var(cfg, "*stdclm"),
        "mscl": _get_var(cfg, "*stdmscldb"),
        "mould": _get_var(cfg, "*stdmould"),
        "plant": _get_var(cfg, "*stdpdb"),
        "sbem": _get_var(cfg, "*stdsbem"),
        "predef": _get_var(cfg, "*stdpredef"),
    }

    # Control file
    ctl = _get_var(cfg, "*ctl")

    # Assessment year
    year = _get_var(cfg, "*year")

    # Get index numbers of list elements for begin of each zone desc.
    idx_zone_begin = [ind for ind, x in enumerate(cfg) if x[0] == "*zon"]
    idx_zone_end = [ind for ind, x in enumerate(cfg) if x[0] == "*zend"]
    n_zones = len(idx_zone_begin)

    # loop through each 'slide' of the cfg_file for the various zone files
    Z = []
    for i in range(n_zones):
        cfg_slice = cfg[idx_zone_begin[i] : idx_zone_end[i]]

        # Get zone no.
        iz_zone = _get_var(cfg_slice, "*zon")

        # Add files to dictionary
        iz_files = {
            "opr": _get_var(cfg_slice, "*opr"),
            "geo": _get_var(cfg_slice, "*geo"),
            "con": _get_var(cfg_slice, "*con"),
            "tmc": _get_var(cfg_slice, "*tmc"),
        }

        # Append to list
        Z.append([int(iz_zone), iz_files])

    # If list is empty return NoneType
    if not Z:
        Z = None

    return cfg, date, paths, databases, ctl, year, Z


def geometry(filepath):
    """
    Reads in an ESP-r geometry file.

    Returns the name and description of the zone.

    Returns the last modified date.

    Returns a list of the vertices, where each element is a list of floats
    specifying the x, y, z coordinate in space.

    Returns a list of the surface edges, where each element is a list of ints
    specifying the vertex numbers that make up the surface.
    Note that these are referenced as 1-indexed.

    Returns a list of the surface attributes, where each element is:
    ['surf name', 'surf position', 'child of (surface name)',
    'useage1', 'useage2', 'construction name', 'optical name',
    'boundary condition', 'dat1', 'dat2']
    """
    geo = _read_file(filepath)

    # Zone name
    name = _get_var(geo, "*Geometry").split(",")[2]

    # Modified date
    date = _get_var(geo, "*date")  # string
    date = datetime.strptime(date, "%a %b %d %H:%M:%S %Y")  # datetime

    # Zone description
    desc = " ".join(geo[2])

    # Need to re-split file to access items with comma following keyword
    file2 = []
    for x in geo:
        file_split = x[0].split(",", 1)
        if file_split:
            file2.append(file_split)

    # Scan through list and get vertices, surface edges and surface props
    vertices = []
    edges = []
    props = []
    for x in file2:
        if x[0] == "*vertex":
            vertices.append([float(y) for y in x[1].split(",")])
        elif x[0] == "*edges":
            dat = x[1].split(",", 1)  # sep. no. of edges from list of vertices
            edges.append([int(y) for y in dat[1].split(",")])
        elif x[0] == "*surf":
            props.append(x[1].split(","))

    areas = []
    components = []
    for i, surface in enumerate(edges):
        vertices_surf_i = pos_from_vert_num_list(vertices, surface)
        components.append(Component(props[i], vertices_surf_i))
        areas.append(area(vertices_surf_i))

    # get base area
    base_list = [x for x in geo if x[0].split(",")[0] == "*base_list"][0]
    # print(base_list)
    # get base_list type
    # TODO(j.allison): test length of base instead of try and except
    try:
        bl_type = base_list[1].split(" ")[1]
    except:
        bl_type = base_list[0].split(",")[-1]

    # base area via list
    if bl_type == "2":
        idx_surfaces = base_list[0].split(",")[2:-1]
        area_base = 0
        for surface in idx_surfaces:
            area_base += areas[int(surface) - 1]
    # manual base area
    elif bl_type == "0":
        area_base = 1
    else:
        area_base = None

    return {
        "name": name,
        "desc": desc,
        "date": date,
        "vertices": vertices,
        "edges": edges,
        "props": props,
        "areas": areas,
        "area_base": area_base,
        "components": components,
    }


def constructions(con_file, geo_file):
    """Get data from construction file."""

    geo_data = geometry(geo_file)
    con_data = _read_file(con_file)

    # Number of surfaces in zone
    n_cons = len(geo_data["edges"])

    # Get number of layers and air gaps in each construction
    n_layers_con = []
    for i in range(n_cons):
        n_layers_con.append([int(con_data[i][0].split(",")[0])] + [int(con_data[i][1])])
    total_layers = sum([x[0] for x in n_layers_con])

    # The start of the construction data is dependent on the number of constructions with air gaps in the zone
    # i.e. n_surfaces + n_surf_with_airgaps = start index of construction layers
    n_con_air_gaps = sum([1 if x[1] > 0 else 0 for x in n_layers_con])

    # Get air gap data (these can be of varying length or none at all)
    air_gap_props = []
    air_gap_data = con_data[n_cons:n_cons+n_con_air_gaps]
    j = 0
    for i, constr in enumerate(n_layers_con):
        if constr[1] == 0:
            air_gap_props.append(None)
        else:
            air_gap_props.append([int(air_gap_data[j][0].split(",")[0])] + split_to_float(air_gap_data[j][1][:-1]))
            j += 1

    # Read all layers
    layer_therm_props_all = []
    for i in range(n_cons + n_con_air_gaps, n_cons + n_con_air_gaps + total_layers):
        layer_therm_props_all.append(
            [float(con_data[i][0].split(",")[0])]
            # + [float(x) for x in con_data[i][1].split(",")]
            + split_to_float(con_data[i][1])
        )

    nidx = list(accumulate([x[0] for x in n_layers_con]))
    layer_therm_props = [layer_therm_props_all[: nidx[0]]]  # first con
    # Rest of cons
    for i in range(n_cons - 1):
        layer_therm_props.append(layer_therm_props_all[nidx[i] : nidx[i + 1]])

    # Read emissivities
    # TODO(j.allison): When there are a lot of layers, these become multi-line
    # emissivity_inside = split_to_float(con_data[n_cons + n_con_air_gaps + total_layers][0])
    # emissivity_outside = split_to_float(con_data[n_cons + n_con_air_gaps + total_layers + 1][0])

    # Read absorptivities
    # absorptivity_inside = split_to_float(con_data[n_cons + n_con_air_gaps + total_layers + 2][0])
    # absorptivity_outside = split_to_float(con_data[n_cons + n_con_air_gaps + total_layers + 3][0])

    return {
        "n_layers_con": n_layers_con,
        "air_gap_props": air_gap_props,
        "layer_therm_props": layer_therm_props,
        # "emissivity_inside": emissivity_inside,
        # "emissivity_outside": emissivity_outside,
        # "absorptivity_inside": absorptivity_inside,
        # "absorptivity_outside": absorptivity_outside,
    }


def controls(filepath):
    """Import model controls."""
    ctl = _read_file(filepath)
    description_overall = " ".join(ctl[0])
    ctl_type = ctl[1][1]
    sensors, actuators, daytypes, ctl_data, start_times, laws, valid, periods = ([] for i in range(8))
    if ctl_type == "Building":
        description_zone = " ".join(ctl[2])
        n_ctl = int(ctl[3][0])
        idx = 4  # start of Control function 1
        for i_ctl in range(n_ctl):
            ctl_data.append([])
            start_times.append([])
            laws.append([])
            valid.append([])
            periods.append([])
            sensors.append(space_data_to_list(ctl[idx + 1]))
            actuators.append(space_data_to_list(ctl[idx + 2]))
            i_daytypes = int(ctl[idx + 3][0])
            if i_daytypes == 0:
                i_daytypes = 4  # calendar daytypes
            daytypes.append(i_daytypes)
            for i_daytype in range(daytypes[i_ctl]):
                ctl_data[i_ctl].append([])
                start_times[i_ctl].append([])
                laws[i_ctl].append([])
                valid[i_ctl].append([int(x) for x in ctl[idx + 4]])
                periods[i_ctl].append(int(ctl[idx + 5][0]))
                for _ in range(periods[i_ctl][i_daytype]):
                    # n_type = int(ctl[10][0])  # unknown use for type
                    laws[i_ctl][i_daytype].append(int(ctl[idx + 6][1].split(" ")[0]))
                    start_times[i_ctl][i_daytype].append(float(ctl[idx + 6][1].split(" ")[-1]))
                    n_items = int(float(ctl[idx + 7][0]))
                    if n_items > 0:
                        ctl_data[i_ctl][i_daytype].append(space_data_to_list(ctl[idx + 8], "float"))
                        idx += 3  # 3 data rows per period
                    else:
                        ctl_data[i_ctl][i_daytype].append(None)
                        idx += 2  # 2 raws when no data items
                idx += 2
            idx += 4
        links = ctl[-1]
    return {
        "description_overall": description_overall,
        "description_zone": description_zone,
        "sensors": sensors,
        "actuators": actuators,
        "daytypes": daytypes,
        "ctl_data": ctl_data,
        "start_times": start_times,
        "laws": laws,
        "valid": valid,
        "periods": periods,
        "links": links,
    } 


def pos_from_vert_num_list(vertices_zone, edges):
    """
    Get x,y,z position of vertices that comprise a surface
    from the zone vertices and their indices as defined in
    the edges list
    """
    vertices_surf = []
    for vertex in edges:
        vertices_surf.append(vertices_zone[vertex - 1])
    return vertices_surf
