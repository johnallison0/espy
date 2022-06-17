# -*- coding: utf-8 -*-
"""
Functions for visualising ESP-r models.

Note that the pyplot functions in here are quick, but 3D plots may not display
correctly due to intrinsic limitations of matplotlib.

Efforts have been made to implement equivalent functionality in VTK, which is
slower but more robust, and requires an OpenGL implementation.
This is a work in progress.
"""

from audioop import add
import itertools
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection
from espy import get
from wand.image import Image
import math
from collections import Counter
import vtk

# pylint: disable-msg=C0103

def set_axes_radius(ax, origin, radius):
    """
    Set axes radius.

    Arguments
        ax: matplotlib.axes.Axes
            e.g. output from plt.gca()
        origin: list or tuple (3), float
            axes origin coordinates
            e.g. [0.,0.,0.]
        radius: float
            axes radius

    Returns
        None (modifies ax in-place)
    """

    ax.set_xlim3d([origin[0] - radius, origin[0] + radius])
    ax.set_ylim3d([origin[1] - radius, origin[1] + radius])
    ax.set_zlim3d([origin[2] - radius, origin[2] + radius])


def set_axes_equal(ax):
    """Make axes of 3D plot have equal scale so that spheres appear as spheres,
    cubes as cubes, etc..  This is one possible solution to Matplotlib's
    ax.set_aspect('equal') and ax.axis('equal') not working for 3D.

    Arguments
        ax: matplotlib.axes.Axes 
            e.g. output from plt.gca()

    Returns
        None (modifies ax in-place)
    """

    limits = np.array([ax.get_xlim3d(), ax.get_ylim3d(), ax.get_zlim3d()])

    origin = np.mean(limits, axis=1)
    radius = 0.5 * np.max(np.abs(limits[:, 1] - limits[:, 0]))
    set_axes_radius(ax, origin, radius)


def set_axes_limits(ax, lims):
    """
    Set axis limits.
    Call set_axes_equal after this function to ensure objects display correctly.

    Arguments
        ax: matplotlib.axes.Axes
            e.g. output from plt.gca()
        lims: list (3), list (2), float
            e.g. [[xmin,xmax],[ymin,ymax],[zmin,zmax]]

    Returns
        None (modifies ax in-place)

    """

    ax.set_xlim(lims[0])
    ax.set_ylim(lims[1])
    ax.set_zlim(lims[2])


def cuboid_data(o, size=(1, 1, 1)):
    """
    Calculate cuboid data from origin and size.

    Arguments
        o: list or tuple (3), float
            coordinates of cuboid origin
            e.g. [0., 0., 0.]
        size: list or tuple (3), float
            size of cuboid
            optional, default (1, 1, 1)

    Returns
        numpy.ndarray, float
            x coordinates of coboid vertices
        numpy.ndarray, float
            y coordinates of cuboid vertices
        numpy.ndarray, float
            z coordinates of cuboid vertices
        float
            largest face area
        float
            cuboid volume
        float
            thickness (volume / largest face area)
    """
    # code taken from
    # https://stackoverflow.com/a/35978146/4124317
    # suppose axis direction: x: to left; y: to inside; z: to upper
    # get the length, width, and height
    l, w, h = size

    areas = [l * w, l * h, w * h]
    idx_max = np.argmax(areas)
    if idx_max == 0:
        area_cross_vertices = [
            [o[0], o[1], o[2] + h / 2],
            [o[0] + l, o[1], o[2] + h / 2],
            [o[0] + l, o[1] + w, o[2] + h / 2],
            [o[0], o[1] + w, o[2] + h / 2],
        ]
    elif idx_max == 1:
        area_cross_vertices = [
            [o[0], o[1] + w / 2, o[2]],
            [o[0] + l, o[1] + w / 2, o[2]],
            [o[0] + l, o[1] + w / 2, o[2] + h],
            [o[0], o[1] + w / 2, o[2] + h],
        ]
    elif idx_max == 2:
        area_cross_vertices = [
            [o[0] + l / 2, o[1] + w, o[2]],
            [o[0] + l / 2, o[1], o[2]],
            [o[0] + l / 2, o[1], o[2] + h],
            [o[0] + l / 2, o[1] + w, o[2] + h],
        ]
    else:
        print("Cannot find cross-section of cuboid")

    # Thickness of construction
    d = l * w * h / np.max(areas)

    x = [
        [o[0], o[0] + l, o[0] + l, o[0], o[0]],
        [o[0], o[0] + l, o[0] + l, o[0], o[0]],
        [o[0], o[0] + l, o[0] + l, o[0], o[0]],
        [o[0], o[0] + l, o[0] + l, o[0], o[0]],
    ]
    y = [
        [o[1], o[1], o[1] + w, o[1] + w, o[1]],
        [o[1], o[1], o[1] + w, o[1] + w, o[1]],
        [o[1], o[1], o[1], o[1], o[1]],
        [o[1] + w, o[1] + w, o[1] + w, o[1] + w, o[1] + w],
    ]
    z = [
        [o[2], o[2], o[2], o[2], o[2]],
        [o[2] + h, o[2] + h, o[2] + h, o[2] + h, o[2] + h],
        [o[2], o[2], o[2] + h, o[2] + h, o[2]],
        [o[2], o[2], o[2] + h, o[2] + h, o[2]],
    ]
    return np.array(x), np.array(y), np.array(z), area_cross_vertices, l * w * h, d


def plot_cuboid(pos=(0., 0., 0.), size=(1., 1., 1.), ax=None, **kwargs):
    """
    Plot a cuboid element.
    
    Arguments
        pos: list or tuple (3), float
            cuboid origin coordinates
            optional, default (0., 0., 0.)
        size: list or tuple (3), float
            cuboid size
            optional, default (1., 1., 1.)
        ax: matplotlib.axes.Axes
            e.g. output from plt.gca()
        **kwargs
            additional arguments to be forwarded to matplotlib.pyplot.plot_surface

    Returns
        None
    """
    if ax is not None:
        X, Y, Z, _, _, _ = cuboid_data(pos, size)
        ax.plot_surface(X, Y, Z, rstride=1, cstride=1, **kwargs)


def plot_predef_ents(vis, vertices):
    """
    Create 3D figure and plot visual entities and mass surfaces, 
    for example for predefined entity, with pyplot.
    Displays plot and will pause until user closes it.

    Arguments
        vis: list, list (6), float
            list of cuboid visual entities
            e.g. [[origin_x, origin_y, origin_z, size_x, size_y, size_z],...]
        vertices: list, list, list (3), float
            list of vertices for mass surfaces e.g.
            e.g. [[[0.,0.,0.],[0.,1.,0.],[1.,1.,0.],[1.,0.,0.]],...]

    Returns
        None
    """

    fig = plt.figure()
    axis = fig.gca(projection="3d")
    axis.set_aspect("equal")

    for ent in vis:
        plot_cuboid(pos=ent[0:3], size=ent[3:6], ax=axis, color="crimson", alpha=0.2)

    for vertices_i in vertices:
        plot_zone_surface(vertices_i, ax=axis)

    set_axes_equal(axis)
    plt.axis("off")
    plt.grid(b=None)
    plt.show()


def plot_zone_surface(vertices, ax=None, facecolour=None, alpha=0.2):
    """
    Plots a surface with pyplot.

    Arguments
        vertices: list, list (3), float
            vertex coordinates
            e.g. [[0., 0., 0.],[0., 1., 0.],...]
        ax: matplotlib.axes.Axes
            e.g. output from plt.gca()
        facecolour: string
            surface colour hash code
            e.g. '#c19a6b'
            optional, default None (i.e. white)
        alpha: float
            opacity
            0.0 - 1.0
            optional, default 0.2

    Returns
        None

    """
    # Close path.
    vertices = vertices + [vertices[0]]
    # Extract x,y,z.
    x = [vertex[0] for vertex in vertices]
    y = [vertex[1] for vertex in vertices]
    z = [vertex[2] for vertex in vertices]
    verts = [list(zip(x, y, z))]
    if facecolour is None:
        surf_outline = Line3DCollection(verts, colors="k")
    else:
        if alpha is not None:
            surf = Poly3DCollection(verts, alpha=alpha)
        else:
            surf = Poly3DCollection(verts)
        surf.set_facecolor(facecolour)
        surf_outline = Line3DCollection(verts, colors="k")
    # Add to axes.
    if ax is not None:
        ax.add_collection3d(surf_outline)
        if facecolour is not None:
            ax.add_collection3d(surf)


def plot_zone(geo_file, ax=None, show_roof=True):
    """
    Plot zone geometry with pyplot.

    Arguments
        geo_file: string
            name of zone geometry file
        ax: matplotlib.axes.Axes
            e.g. output from plt.gca()
        show_roof: boolean
            If True show roof surface(s)
            optional, default True

    Returns
        None

    Example
        fig = plt.figure()
        ax = fig.gca(projection='3d')
        plot.plot_zone(geo_file, ax=ax)
        plt.show()

    """

    geo = get.geometry(geo_file)
    vertices = geo["vertices"]
    edges = geo["edges"]

    # Set up axes.
    if (ax):
        ax_lims=[[0,1],[0,1],[0,1]]
        ax_lims[0][0] = min([a[0] for a in vertices])-0.5
        ax_lims[0][1] = max([a[0] for a in vertices])+0.5
        ax_lims[1][0] = min([a[1] for a in vertices])-0.5
        ax_lims[1][1] = max([a[1] for a in vertices])+0.5
        ax_lims[2][0] = min([a[2] for a in vertices])-0.5
        ax_lims[2][1] = max([a[2] for a in vertices])+0.5
        set_axes_limits(ax,ax_lims)
        set_axes_equal(ax)


    for i, surface in enumerate(edges):
        # Translate vertex no. to vertex x,y,z pos.
        vs = []
        for vertex in surface:
            vs.append(vertices[vertex - 1])
        # Plot surface from vertex coordinates)
        if (
            geo["props"][i][1] == "CEIL" or geo["props"][i][1] == "SLOP"
        ) and not show_roof:
            print("not showing roof")
        else:
            if geo["props"][i][6] == "OPAQUE" and geo["props"][i][7] == "EXTERIOR":
                if "DOOR" in geo["props"][i][3] or "FRAME" in geo["props"][i][3]:
                    plot_zone_surface(vs, ax=ax, facecolour="#c19a6b", alpha=None)
                else:
                    # default grey surface
                    plot_zone_surface(vs, ax=ax, facecolour="#afacac", alpha=None)
            elif geo["props"][i][6] == "OPAQUE" and geo["props"][i][7] == "ANOTHER":
                if "DOOR" in geo["props"][i][3]:
                    # door
                    plot_zone_surface(vs, ax=ax, facecolour="#f5f2d0", alpha=None)
                else:
                    # default 25% lighter surface
                    plot_zone_surface(vs, ax=ax, facecolour="#ffffff", alpha=None)
            elif geo["props"][i][6] == "OPAQUE" and geo["props"][i][7] == "SIMILAR":
                # opaque, similar
                plot_zone_surface(vs, ax=ax, facecolour="#d8e4bc", alpha=None)
            elif geo["props"][i][6] == "OPAQUE" and geo["props"][i][7] == "GROUND":
                plot_zone_surface(vs, ax=ax, facecolour="#654321", alpha=None)
            else:
                # Transparent surfaces
                plot_zone_surface(vs, ax=ax, facecolour="#008db0")


def plot_construction(con_data, vertices_surf, ax=None):
    """
    Plot 3D construction.
    
    Arguments
        con_data: list, list
            construction data
            output from get.constructions(...)["layer_therm_props"]
        vertices_surf: list, list (3), float
            list of vertex coordinates
            e.g. [[0., 0., 0.],[0., 1., 0.],...]
        ax: matplotlib.axes.Axes
            e.g. output from plt.gca()

    Returns
        None
    """
    con_data.reverse()
    thickness = [x[3] for x in con_data]
    normal = get.calculate_normal(vertices_surf)
    start = 0
    for i, _ in enumerate(con_data):
        a4 = vertices_surf + [vertices_surf[0]]

        X = [
            # [v[0] for v in a1],
            # [v[0] for v in a2],
            [v[0] + (start + thickness[i]) * normal[0] for v in a4],
            [v[0] + start * normal[0] for v in a4],
        ]

        Y = [
            # [v[1] for v in a1],
            # [v[1] for v in a2],
            [v[1] + (start + thickness[i]) * normal[1] for v in a4],
            [v[1] + start * normal[1] for v in a4],
        ]

        Z = [
            # [v[2] for v in a1],
            # [v[2] for v in a2],
            [v[2] + (start + thickness[i]) * normal[2] for v in a4],
            [v[2] + start * normal[2] for v in a4],
        ]

        ax.plot_surface(np.array(X), np.array(Y), np.array(Z), rstride=1, cstride=1)

        start += thickness[i]


def construction_schematic(
    constr_name, constr_data, air_gap_data, figsize=(3.54, 2.655), savefig=False
):
    """
    Plot 2D construction schematic.
    If the figure is saved, uses wand module (ImageMagick)
    to trim whitespace from the image.

    Arguments
        constr_name: string
            name of construction
        constr_data: list, list
            construction data
            output from get.constructions(...)["layer_therm_props"]
        air_gap_data: list, list
            air gap data
            output from get.constructions(...)["air_gap_props"]
        figsize: list or tuple (2), float
            length and height of figure in inches
        savefig: boolean
            if True save figure in images directory
            if False display plot and pause
            optional, default False

    Returns
        None
    """
    # TODO(j.allison): colour layers according to material type.
    #     This will be hard as the material name is not stored in any model file.
    #     Will have to look up the construction in the constr.db and extract the
    #     names. With the name extracted, will then have to look up the category
    #     in the material.db.
    thick_tot = round(sum([x[3] for x in constr_data]), 3)
    y_constr = 500
    air_gap_props_i = air_gap_data
    con_data_i = constr_data
    if air_gap_props_i is not None:
        idx_air_gaps_i = air_gap_props_i[0::2]
    else:
        idx_air_gaps_i = []
    dx = [0] + [x[3] for x in con_data_i]
    x_dat = [x * 1000 for x in list(itertools.accumulate(dx))]

    # plt.style.use('grayscale')
    fig, ax = plt.subplots(figsize=figsize, dpi=220)
    fig.canvas.set_window_title(constr_name)
    ax.vlines(x_dat, 0, y_constr, linewidth=0.5)
    for i, _ in enumerate(x_dat[0:-1]):
        layer = i + 1
        if i == 0:
            name = "Ext"
        elif i == len(con_data_i) - 1:
            name = "Int"
        else:
            name = i + 1
        ax.text(x_dat[i], y_constr + 10, name)
        if layer in idx_air_gaps_i:
            continue
        else:
            ax.fill_betweenx(
                (0, y_constr), x_dat[i], x_dat[i + 1], alpha=0.4, color="grey"
            )
    ax.set_aspect("equal")
    ax.set_xticks([0, max(x_dat)])
    ax.set_xlim(0 - 10, 1000 * thick_tot + 10)
    ax.set_ylim(0, y_constr + 10)
    ax.yaxis.set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    plt.tight_layout()
    file_name = []
    if savefig:
        file_name = f"../images/{constr_name}.png"
        plt.savefig(file_name, bbox_inches="tight", pad_inches=0, dpi=220)
        with Image(filename=file_name) as img:
            img.trim(color=None, fuzz=0)
            img.save(filename=file_name)
    else:
        plt.show()
    return file_name


def plot_zone_constructions(con_file, geo_file, ax=None):
    """
    Plot all zone constructions in 3D.

    Arguments
        con_file: string
            zone construction file name
        geo_file: string
            zone geometry file name
        ax: matplotlib.axes.Axes
            e.g. output from plt.gca()

    Returns
        None
    """
    zone_geometry = get.geometry(geo_file)
    con = get.constructions(con_file, geo_file)
    layer_therm_props = con["layer_therm_props"]

    for i, _ in enumerate(zone_geometry["edges"]):
        con_data = layer_therm_props[i]
        surface = zone_geometry["edges"][i]
        # map vertex indices in edges list to x,y,z vertices
        vertices_surf_i = []
        for vertex in surface:
            vertices_surf_i.append(zone_geometry["vertices"][vertex - 1])
        plot_construction(con_data, vertices_surf_i, ax=ax)


def plot_building_component(geo_file, con_file, idx_surface, ax=None, show_roof=True):
    """
    Plot a particular surface construction in 3D.

    This function plots a 3D building component (wall, floor, roof etc.)
    from its surface geometry and construction data.

    The inside surface is plotted as white, while the external surface colour
    is dependent on the surface properties from the geometry file.

    Arguments
        geo_file: string
            zone geometry file name
        con_file: string
            zone construction file name
        idx_surface: integer
            surface index
        ax: matplotlib.axes.Axes
            e.g. output from plt.gca()
        show_roof: boolean
            if True show roof surface(s)
            optional, default True

    Returns
        None

    """

    # TODO(j.allison): Create new figure and axes if none are provided

    # Read geometry file
    zone_geometry = get.geometry(geo_file)
    surface_props = zone_geometry["props"][idx_surface]

    # Get vertex numbers that comprise surface
    surface_edges = zone_geometry["edges"][idx_surface]

    # Get vertex positions that comprise surface
    vertices_surf = get.pos_from_vert_num_list(zone_geometry["vertices"], surface_edges)

    # Plot inside (zone-facing) surface
    if (surface_props[1] == "CEIL" or surface_props[1] == "SLOP") and not show_roof:
        pass
    else:
        if surface_props[6] == "OPAQUE":
            plot_zone_surface(vertices_surf, ax=ax, facecolour="w", alpha=None)
        else:
            plot_zone_surface(vertices_surf, ax=ax, facecolour="#008db0")

    # Plot construction layers
    con = get.constructions(con_file, geo_file)
    layer_therm_props = con["layer_therm_props"]
    con_data = layer_therm_props[idx_surface]
    if (surface_props[1] == "CEIL" or surface_props[1] == "SLOP") and not show_roof:
        pass
    else:
        plot_construction(con_data, vertices_surf, ax=ax)

    # -------------------------------------
    # Plot outer surface
    # -------------------------------------
    normal = get.calculate_normal(vertices_surf)
    # vertices_surf += [vertices_surf[0]]
    total_thickness = sum([x[3] for x in con_data])
    # Extend vertex position along surface normal by the total thickness
    x_pos = [v[0] + total_thickness * normal[0] for v in vertices_surf]
    y_pos = [v[1] + total_thickness * normal[1] for v in vertices_surf]
    z_pos = [v[2] + total_thickness * normal[2] for v in vertices_surf]
    # Restructure to surface vertices
    # Can probably do this in a zip list comprehension...
    vertices_surf_outer = []
    for i, _ in enumerate(vertices_surf):
        vertices_surf_outer.append([x_pos[i], y_pos[i], z_pos[i]])
    if (surface_props[1] == "CEIL" or surface_props[1] == "SLOP") and not show_roof:
        pass
    else:
        if surface_props[6] == "OPAQUE" and surface_props[7] == "EXTERIOR":
            if "DOOR" in surface_props[3] or "FRAME" in surface_props[3]:
                # door or frame
                plot_zone_surface(
                    vertices_surf_outer, ax=ax, facecolour="#c19a6b", alpha=None
                )
            else:
                # default grey surface
                plot_zone_surface(
                    vertices_surf_outer, ax=ax, facecolour="#afacac", alpha=None
                )
        elif surface_props[6] == "OPAQUE" and surface_props[7] == "ANOTHER":
            if "DOOR" in surface_props[3]:
                # door
                plot_zone_surface(
                    vertices_surf_outer, ax=ax, facecolour="#f5f2d0", alpha=None
                )
            else:
                # default 25% lighter surface
                plot_zone_surface(
                    vertices_surf_outer, ax=ax, facecolour="#ffffff", alpha=None
                )
        elif surface_props[6] == "OPAQUE" and surface_props[7] == "SIMILAR":
            plot_zone_surface(
                vertices_surf_outer, ax=ax, facecolour="#d8e4bc", alpha=None
            )
        elif surface_props[6] == "OPAQUE" and surface_props[7] == "GROUND":
            plot_zone_surface(
                vertices_surf_outer, ax=ax, facecolour="#654321", alpha=None
            )
        else:
            # Transparent surfaces
            plot_zone_surface(vertices_surf_outer, ax=ax, facecolour="#008db0")

            
def vtk_view(actors, edge_actors, outlines):
    """
    VTK visualisation setup and render.
    
    Arguments
        actors: list, vtk.vtkOpenGLActor
            surface actors
            elements are output from generate_vtk_actors(...)[0]
        edge_actors: list, vtk.vtkOpenGLActor
            mesh edge actors
            elements are output from generate_vtk_actors(...)[1]
        outlines: list, vtk.vtkOpenGLActor
            outline actors
            elements are output from generate_vtk_actors(...)[2]

    Returns
        None
    
    Example
        geo = get.geometry(geometry_file)
        for comp in geo['components']:
            sa,ea,oa = plot.generate_vtk_actors(
                comp.generate_vtk_surface(),
                comp.set_outer_colour())
            sas.append(sa)
            eas.append(ea)
            oas.append(oa)
        plot.vtk_view(sas,eas,oas)
    """

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
    """
    Generates 3 VTK actors.

    Returns 3 VTK actors, which represents an object in a rendered scene.

    Arguments
        surf_obj: vtk.vtkPolyDataAlgorithm
            vtkObject that defines the surface
        outer_colour: list
            Colour and opacity of surface 
            e.g. ["#f5f2d0", 1]
        show_edges: boolean
            If True show edges of triangle mesh
            optional, default False
        show_outline: boolean
            If True show surface outline
            optional, default True

    Returns
        surface_actor: vtk.vtkOpenGLActor
            2D component surface projected on 3D plane
        edge_actor: vtk.vtkOpenGLActor
            surface mesh edges
        outline_actor: vtk.vtkOpenGLActor
            boundary outline of surface

    Example
        geo = get.geometry(geometry_file)
        for comp in geo['components']:
            sa,ea,oa = plot.generate_vtk_actors(
                comp.generate_vtk_surface(),
                comp.set_outer_colour())
            sas.append(sa)
            eas.append(ea)
            oas.append(oa)
        plot.vtk_view(sas,eas,oas)

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
    surface_actor.GetProperty().SetColor(
        [x / 255 for x in colors.HTMLColorToRGB(outer_colour[0])]
    )
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
    """
    Class defining a zone surface.
    """

    def __init__(self, property_list, child_verts, vertices_surf):
        """
        Self-creation method.
        
        Arguments
            property_list: list
                surface properties
                output from get.geometry(...)["props"])
            child_verts: list, list, list (3), float
                child surface vertex coordinates
            vertices_surf: list, list (3), float
                surface vertex coordinates

        Returns
            Component object

        Example
            surface_component = plot.Component(property_list, child_verts, vertices_surf)
        """
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
        self.child_verts = child_verts
        self.vertices_surf = vertices_surf

    def generate_vtk_surface(self):
        """
        Generate building component surface as a VTK object.

        Arguments
            None

        Returns
            surf_obj: vtk.vtkPolyDataAlgorithm
                suitable for input to generate_vtk_actors(...)

        Example
            geo = get.geometry(geometry_file)
            for comp in geo['components']:
                sa,ea,oa = plot.generate_vtk_actors(
                    comp.generate_vtk_surface(),
                    comp.set_outer_colour())
                sas.append(sa)
                eas.append(ea)
                oas.append(oa)
            plot.vtk_view(sas,eas,oas)

        """

        # Check for duplicate vertices
        dups = [
            k for k, v in Counter(tuple(x) for x in self.vertices_surf).items() if v > 1
        ]
        if not dups:
            # Normal surface without holes

            # Setup points
            points = vtk.vtkPoints()
            for vertex in self.vertices_surf:
                points.InsertNextPoint(vertex[0], vertex[1], vertex[2])

            # Create the polygon
            polygon = vtk.vtkPolygon()
            polygon.GetPointIds().SetNumberOfIds(
                len(self.vertices_surf)
            )  # make a polygon
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
            # This surface has duplicate vertices and is therefore a 'weakly simple polygon'.
            # Extract outer and inner polygons.
            vertices_surf_outer, vertices_surfs_inner = get_outer_inner(self.vertices_surf)

            # Make sure the inner polygons match child surfaces.
            # There might be more children, for example doors, that have not
            # been caught above because they are not bounded by duplicate vertices.
            if len(vertices_surfs_inner) < len(self.child_verts):
                # There are additional children.
                # First we need to find which ones have already been dealt with.
                for child in self.child_verts:
                    for i,inner in enumerate(vertices_surfs_inner):
                        # If they have 4 verts in common, it's a match.
                        matches = 0
                        is_match = False
                        for v in inner:
                            if v in child:
                                matches += 1
                                if matches == 4:
                                    is_match = True
                                    break
                        if is_match: break
                    if not is_match:
                        # This child is not represented by an inner polygon; add one.
                        # Extract the outer polygon of the child in case it also has children.
                        x,_ = get_outer_inner(child)
                        x.reverse()
                        vertices_surfs_inner.append(x)

            # Setup points for outside polygon.
            points = vtk.vtkPoints()
            polys = vtk.vtkCellArray()
            i = 0
            for vertex in vertices_surf_outer:
                points.InsertPoint(i, vertex[0], vertex[1], vertex[2])
                i += 1

            # For each inner polygon, add points that aren't already in the points list,
            # and form the hole.
            for vertices_surf_inner in vertices_surfs_inner:
                poly=vtk.vtkPolygon()
                for vertex in vertices_surf_inner:
                    isin, j = is_point_in_surf(vertex, vertices_surf_outer)
                    if isin:
                        poly.GetPointIds().InsertNextId(j)
                    else:
                        points.InsertPoint(i, vertex[0], vertex[1], vertex[2])
                        poly.GetPointIds().InsertNextId(i)
                        i += 1
                polys.InsertNextCell(poly)

            # from vtk.util import numpy_support
            # print(numpy_support.vtk_to_numpy(points.GetData()))

            # Define transform to rotate the surface into the X-Y plane for Delaunay filter.
            transform = vtk.vtkTransform()
            transform.Identity()

            # Normal vectors of the two planes.
            normSurf = calculate_normal(vertices_surf_outer)
            normXY = [0., 0., 1.]

            # Equations of the two planes [a,b,c,d] where ax + by + cz + d = 0.
            plnSurf = normSurf + [-(
                normSurf[0]*vertices_surf_outer[0][0]+
                normSurf[1]*vertices_surf_outer[0][1]+
                normSurf[2]*vertices_surf_outer[0][2])]
            plnXY = normXY + [0.]

            # Now calculate rotation angle and axis.
            try:
                plnInt,_ = calculate_plane_intersect(plnSurf,plnXY)
            except np.linalg.LinAlgError: # No rotation is needed.
                pass
            else:
                D = np.degrees(np.arccos(np.dot(normSurf,normXY)))
                transform.RotateWXYZ(D,plnInt)

            # x = vtk.vtkPoints()
            # transform.TransformPoints(points,x)
            # print(numpy_support.vtk_to_numpy(x.GetData()))

            # Setup polydata.
            iPolyData = vtk.vtkPolyData()
            sPolyData = vtk.vtkPolyData()
            iPolyData.SetPoints(points)
            sPolyData.SetPoints(points)
            sPolyData.SetPolys(polys)

            # Notice this trick. The SetInput() method accepts a vtkPolyData that
            # is also the input to the Delaunay filter. The points of the
            # vtkPolyData are used to generate the triangulation; the polygons are
            # used to create constraint regions for each hole. The polygons are carefully
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

            surf_obj.SetInputData(iPolyData)
            surf_obj.SetSourceData(sPolyData)
            surf_obj.SetTransform(transform)
            # surf_obj.SetProjectionPlaneMode(vtk.VTK_BEST_FITTING_PLANE)

            # print(numpy_support.vtk_to_numpy(surf_obj.GetOutput().GetDataObjectType()))

        return surf_obj

    def set_outer_colour(self):
        """
        Set default colour of otherside surface based on boundary conditions.

        Arguments
            None

        Returns
            surf_colour: list (2)
                colour hash code and opacity
                suitable for input to generate_vtk_actors(...)
                e.g. ["#F8F4FF", 1.]

        Example        
            sas = []
            eas = []
            oas = []
            geo = get.geometry(geometry_file)
            for comp in geo['components']:
                sa,ea,oa = plot.generate_vtk_actors(
                    comp.generate_vtk_surface(),
                    comp.set_outer_colour())
                sas.append(sa)
                eas.append(ea)
                oas.append(oa)
            plot.vtk_view(sas,eas,oas)
        """

        default_colours = {
            "OPAQUE_ANOTHER": ["#F8F4FF", 1],
            "OPAQUE_ANOTHER_WALL": ["#F8F4FF", 1],
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
            "OPAQUE_GROUND_WALL": ["#654321", 1],
            "OPAQUE_SIMILAR": ["#d8e4bc", 1],
            "OPAQUE_SIMILAR_WALL": ["#d8e4bc", 1],
            "OPAQUE_SIMILAR_DOOR": ["#f5f2d0", 1],
            "OPAQUE_SIMILAR_GRILL": ["#c19a6b", 1],
            "OPAQUE_SIMILAR_PARTN": ["#d8e4bc", 1],
            "TRANSP_SIMILAR": [" #0000FF", 0.2],
            "TRANSP_ANOTHER_FICT": [" #0000FF", 0.2],
            "TRANSP_ANOTHER_WINDOW": [" #008db0", 0.2],
            "OPAQUE_ANOTHER_FURNI": ["#838B8B", 1],
            "OPAQUE_CONSTANT_FURNI": ["#838B8B", 1]
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


def is_point_in_surf(point, verts, tol = 0.0001):
    """
    Checks if point p is already in list of vertices verts
    within tolerance tol.
    
    Arguments
        point: list (3), float
            coordinates of point to check
            e.g. [1., 1., 0.]
        verts: list, list (3), float
            list of vertex point coordinates
        tol: float
            tolerance of total distance
            optional, default 0.0001
        
    Returns
        boolean
            True if point is found in verts
        i: integer or None    
            index of existing vertex if point found
    """
    for i,v in enumerate(verts):
        if dist(point,v) < tol: return True, i
    return False, None


def get_outer_inner(verts, add_intermediate = True):
    """
    Process list of vertices, removing duplicates and
    separating outer and inner polygons into lists.
    Optionally adds intermediate vertices using insert_edge.

    Arguments
        verts: list, list (3), float
            list of vertex coordinates
            e.g. [[0., 0., 0.], [1., 0., 0], ...]
        add_intermediate: boolean
            inserts intermediate vertices if True
            optional, default True

    Returns
        outer: list, list (3), float
            outer polygon vertex coordinates
        inners: list, list, list (3), float
            vertex coordinates for each inner polygon
    """
    # Get indices of duplicate vertices.
    dups = [i for i, x in enumerate(verts) if verts.count(x) > 1]

    if not dups: 
        # No duplicates, so we don't need to extract the outer,
        # only add intermediate vertices.
        if add_intermediate:
            outer = []
            outer.append(verts[0])
            for x in verts[1:]:
                insert_edge(outer,outer[-1],x)
            insert_edge(outer,outer[-1],outer[0],insert_v2=False)
        else:
            outer = verts
        inners = []
    else:
        # Go through the vertices, remove duplictaes, and separate
        # outer and inner polygons.
        iin = 0
        id = 0
        outer = []
        inners = []
        for i,x in enumerate(verts):
            if i == dups[id]:  # This is a duplicate vertex.
                if id < len(dups)-1: id += 1
                if iin:  # We're currently doing an inner polygon.
                    if iin == 1:  # This is the start.
                        inners[-1].append(x)
                        iin += 1
                    elif iin == 2:  # This is the end.
                        # Add the last intermediate vertices.
                        if add_intermediate:
                            insert_edge(inners[-1],inners[-1][-1],inners[-1][0],insert_v2=False)
                        iin += 1
                    elif iin == 3:  # Back to the outer.
                        # This is still a duplicate so we don't need to insert this,
                        # but we do need to check if we're going straight into another inner.
                        if i+1 == dups[id]:  # Another duplicate is next.
                            # We are starting a new inner polygon.
                            inners.append([])
                            iin = 1
                        else:  # We're back to the outer.
                            iin = 0
                else:  # We're starting an inner.
                    if not iin:
                        if outer and add_intermediate:
                            insert_edge(outer,outer[-1],x)
                        else:
                            outer.append(x)
                    inners.append([])
                    iin = 1
            else:  # This is not a duplicate.
                if not iin:
                    if outer and add_intermediate:
                        insert_edge(outer,outer[-1],x)
                    else:
                        outer.append(x)
                else:  # We're currently in an inner polygon.
                    if add_intermediate:
                        insert_edge(inners[-1],inners[-1][-1],x)
                    else:
                        inners[-1].append(x)

        # We need to add one final intermediate between the last and the first vertices.
        if add_intermediate:
            insert_edge(outer,outer[-1],outer[0],insert_v2=False)

    return outer, inners


def dist(v1, v2):
    """
    Get distance between two 3D points v1 and v2.

    Arguments
        v1: list (3), float
            first point coordinates
            e.g. [1., 1., 0.]
        v2: list (3), float
            second point coordinates

    Returns
        float
            distance between the two points
    """

    a1 = np.array(v1)
    a2 = np.array(v2)
    return np.sqrt(np.sum((a1-a2)**2, axis=0))


def insert_edge(verts, v1, v2, insert_v1 = False, insert_v2 = True):
    """
    Insert the edge between vertices v1 and v2 into list verts.
    Inserts intermediate vertices, ensuring that no edge is greater than 1m.

    Arguments
        verts: list, list (3), float
            list of vertices to insert edge into
        v1: list (3), float
            coordinates for start vertex of edge
        v2: list (3), float
            coordinates for end vertex of edge
        insert_v1: boolean
            inserts v1 into verts if True
            optional, default False
        insert_v2: boolean
            inserts v2 into verts if True
            optional, default True

    Returns
        None (modifies verts in-place)
    """

    if insert_v1: verts.append(v1)
    d = dist(v1,v2)
    if d > 1.:
        n = np.ceil(d)
        d1 = (v2[0]-v1[0]) / (n)
        d2 = (v2[1]-v1[1]) / (n)
        d3 = (v2[2]-v1[2]) / (n)
        for i in range(1,int(n)):
            verts.append([
                v1[0] + d1 * (i),
                v1[1] + d2 * (i),
                v1[2] + d3 * (i)])
    if insert_v2: verts.append(v2)


def normalized(X):
    """
    Normalises magnitude of vector.

    Code adapted from:
    https://gist.github.com/marmakoide/79f361dd613f2076ece544070ddae6ab

    Arguments
        X: list (3), float
            vector

    Returns
        float
            normalised vector
    """

    return X / np.sqrt(np.sum(X ** 2))


def calculate_plane_intersect(A,B):
    """
    Calculates a line at the intersection of two planes.

    Code adapted from:
    https://gist.github.com/marmakoide/79f361dd613f2076ece544070ddae6ab

    Arguments
        A: list (4), float
            plane equation [a,b,c,d] where ax + by + cz + d = 0
        B: list (4), float
            as A

    Returns
        U: list (3), float
            direction vector of intersection line
        numpy.ndarray (3), float
            coordinates of a point on the line.
    """
    
    U = normalized(np.cross(A[:-1], B[:-1]))
    M = np.array((A[:-1], B[:-1], U))
    X = np.array((-A[-1], -B[-1], 0.))
    return U, np.linalg.solve(M, X)	


def calculate_normal(p):
    """
    Newell's method for calculating the normal of an arbitrary 3D polygon.

    Arguments
        p: list, list (3), float
            polygon vertex coordinates

    Returns
        nn: list (3), float
            normal direction vector
    """

    normal = [0, 0, 0]
    for i, _ in enumerate(p):
        j = (i + 1) % len(p)
        normal[0] += (p[i][1] - p[j][1]) * (p[i][2] + p[j][2])
        normal[1] += (p[i][2] - p[j][2]) * (p[i][0] + p[j][0])
        normal[2] += (p[i][0] - p[j][0]) * (p[i][1] + p[j][1])
    # normalise
    nn = [0, 0, 0]
    nn[0] = normal[0] / math.sqrt(
        (normal[0]) ** 2 + (normal[1]) ** 2 + (normal[2]) ** 2)
    nn[1] = normal[1] / math.sqrt(
        (normal[0]) ** 2 + (normal[1]) ** 2 + (normal[2]) ** 2)
    nn[2] = normal[2] / math.sqrt(
        (normal[0]) ** 2 + (normal[1]) ** 2 + (normal[2]) ** 2)
    return nn
