"""Functions for importing and reading ESP-r files"""
from datetime import datetime
from itertools import accumulate

import numpy as np

from espy.utils import split_to_float

# pylint: disable-msg=C0103


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
    nn[0] = normal[0]/(abs(normal[0])+abs(normal[1])+abs(normal[2]))
    nn[1] = normal[1]/(abs(normal[0])+abs(normal[1])+abs(normal[2]))
    nn[2] = normal[2]/(abs(normal[0])+abs(normal[1])+abs(normal[2]))
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
    return abs(result / 2)


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
    for _, surface in enumerate(edges):
        vertices_surf_i = []
        # Get x,y,z for surface from vertex index
        for vertex in surface:
            vertices_surf_i.append(vertices[vertex - 1])
        areas.append(area(vertices_surf_i))
        # print("{}: {:.3f} m^2".format(zone_info["props"][zone_id][0], area(vertices_surf_i)))

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

    # The start of the construction data is dependent on the number of air gaps in the zone
    # i.e. n_surfaces + n_airgaps = start index of construction layers
    n_con_air_gaps = sum([1 if x[1] > 0 else 0 for x in n_layers_con])

    # Get air gap data (these can be of varying length)
    air_gap_props = []
    for i in range(n_cons, n_cons + n_con_air_gaps):
        air_gap_props.append(
            [int(con_data[i][0].split(",")[0])] + split_to_float(con_data[i][1][:-1])
        )

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
    emissivity_inside = split_to_float(con_data[n_cons + n_con_air_gaps + total_layers][0])
    emissivity_outside = split_to_float(con_data[n_cons + n_con_air_gaps + total_layers + 1][0])

    # Read absorptivities
    absorptivity_inside = split_to_float(con_data[n_cons + n_con_air_gaps + total_layers + 2][0])
    absorptivity_outside = split_to_float(con_data[n_cons + n_con_air_gaps + total_layers + 3][0])

    return (
        n_layers_con,
        air_gap_props,
        layer_therm_props,
        emissivity_inside,
        emissivity_outside,
        absorptivity_inside,
        absorptivity_outside,
    )
