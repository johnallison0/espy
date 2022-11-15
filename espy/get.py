"""Functions for importing and reading ESP-r files"""
import csv
from datetime import datetime
from itertools import accumulate
from espy.utils import space_data_to_list, split_to_float,area
from espy import plot

# pylint: disable-msg=C0103
# pylint: disable=no-member

def zone_selection(cfg_file, zone_input):
    """Maps requested zone selection to ESP-r menu selection."""
    # TODO: This will not work if zone on secondary page
    # Read cfg file for list of zones
    cfg = config(cfg_file)
    zones = cfg["zones"]

    # Loop through for list of zone names
    zone_names = []
    for ind, _ in enumerate(zones):
        file_path = zones[ind][1]["geo"]
        zone_names.append(geometry(file_path)["name"])

    # format "id:<zone name>"
    if zone_input[:3] == "id:":
            selected_zone = zone_input[3:]
            try:
                ind = zone_names.index(selected_zone)
                zone_select = chr(96 + ind + 1)
                geo_file = zones[ind][1]["geo"]
            except ValueError:
                print("zone selection error, '{}' not found".format(selected_zone))
                zone_select = None
                geo_file = None
    # Assume single letter selection if not prepended with id and len(1)
    # TODO: can expand to check if this zone exists i.e. if asking for 'b' but there's only 1 zone...
    elif len(zone_input) == 1:
        zone_select = zone_input[0]
        idx_zone = ord(zone_input[0]) - 96 - 1
        geo_file = zones[idx_zone][1]["geo"]
    else:
        print(
            "zone selection error for '{}', check input format".format(zone_input)
        )
        zone_select = None
        geo_file = None
    return zone_select, geo_file


def surface_selection(geo_file, surf_input):
    """Maps requested surface selection to ESP-r menu selection."""
    # TODO: This will not work if surface on secondary page
    geo = geometry(geo_file)
    props = geo["props"]

    # Loop through for list of zone names
    surf_names = []
    for surf in props:
        surf_names.append(surf[0])

    # format "id:<zone name>"
    if surf_input[:3] == "id:":
            selected_surf = surf_input[3:]
            try:
                ind = surf_names.index(selected_surf)
                surf_select = chr(96 + ind + 1)
            except ValueError:
                print("surface selection error, '{}' not found".format(selected_surf))
                surf_select = None
    # Assume single letter selection if not prepended with id and len(1)
    # TODO: can expand to check if this zone exists i.e. if asking for 'b' but there's only 1 zone...
    elif len(surf_input) == 1:
        surf_select = surf_input[0]
    else:
        print(
            "surface selection error for '{}', check input format".format(surf_input)
        )
        surf_select = None
    return surf_select


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

    return {
        "cfg": cfg,
        "date": date,
        "paths": paths,
        "databases": databases,
        "ctl": ctl,
        "year": year,
        "zones": Z,
    }


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
    child_verts = []
    for x in file2:
        if x[0] == "*vertex":
            vertices.append([float(y) for y in x[1].split(",")])
        elif x[0] == "*edges":
            dat = x[1].split(",", 1)  # sep. no. of edges from list of vertices
            edges.append([int(y) for y in dat[1].split(",")])
        elif x[0] == "*surf":
            props.append(x[1].split(","))
        child_verts.append(None)

    # Assemble lists of child vertices for each surface.
    for i, prop in enumerate(props):
        if prop[2] != '-':
            try:
                iParent = [a[0] for a in props].index(prop[2])
            except ValueError:
                # print('Warning: parent surface '+prop[2]+' for child '+prop[0]+' does not exist')
                pass
            else:
                if not child_verts[iParent]:
                    child_verts[iParent] = []
                child_verts[iParent].append(pos_from_vert_num_list(vertices,edges[i]))

    areas = []
    components = []
    for i, surface in enumerate(edges):
        vertices_surf_i = pos_from_vert_num_list(vertices, surface)
        components.append(plot.Component(props[i], child_verts[i], vertices_surf_i))
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

    # The start of the construction data is dependent on the number of constructions
    # with air gaps in the zone
    # i.e. n_surfaces + n_surf_with_airgaps = start index of construction layers
    n_con_air_gaps = sum([1 if x[1] > 0 else 0 for x in n_layers_con])

    # Get air gap data (these can be of varying length or none at all)
    air_gap_props = []
    air_gap_data = con_data[n_cons : n_cons + n_con_air_gaps]
    j = 0
    for i, constr in enumerate(n_layers_con):
        if constr[1] == 0:
            air_gap_props.append(None)
        else:
            air_gap_props.append(
                [int(air_gap_data[j][0].split(",")[0])]
                + [float(a) for a in air_gap_data[j][1][:-1].split()]
            )
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
    j = 0
    e_in = con_data[n_cons + n_con_air_gaps + total_layers + j][0].split(",")
    while e_in[-1] == "":
        j += 1
        e_in = e_in[:-1]
        e_in += con_data[n_cons + n_con_air_gaps + total_layers + j][0].split(",")
    e_in = [float(x) for x in e_in]

    j += 1
    e_out = con_data[n_cons + n_con_air_gaps + total_layers + j][0].split(",")
    while e_out[-1] == "":
        j += 1
        e_out = e_out[:-1]
        e_out += con_data[n_cons + n_con_air_gaps + total_layers + j][0].split(",")
    e_out = [float(x) for x in e_out]

    # Read absorptivities
    j += 1
    a_in = con_data[n_cons + n_con_air_gaps + total_layers + j][0].split(",")
    while a_in[-1] == "":
        j += 1
        a_in = a_in[:-1]
        a_in += con_data[n_cons + n_con_air_gaps + total_layers + j][0].split(",")
    a_in = [float(x) for x in a_in]

    j += 1
    a_out = con_data[n_cons + n_con_air_gaps + total_layers + j][0].split(",")
    while a_out[-1] == "":
        j += 1
        a_out = a_out[:-1]
        a_out += con_data[n_cons + n_con_air_gaps + total_layers + j][0].split(",")
    a_out = [float(x) for x in a_out]

    # Append emissivities and solar absorpt to layer construction
    layer_therm_props = list(layer_therm_props)
    for i, con_props in enumerate(layer_therm_props):
        for j, _ in enumerate(con_props):
            if j == 0:
                layer_therm_props[i][j] += [e_out[i], a_out[i]]
            elif j == (len(con_props) - 1):
                layer_therm_props[i][j] += [e_in[i], a_in[i]]
            else:
                layer_therm_props[i][j] += [None, None]
    # print("debug")
    return {
        "n_layers_con": n_layers_con,
        "air_gap_props": air_gap_props,
        "layer_therm_props": layer_therm_props,
    }


def controls(filepath):
    """Import model controls."""
    ctl = _read_file(filepath)
    description_overall = " ".join(ctl[0])
    ctl_type = ctl[1][1]
    sensors, actuators, daytypes, ctl_data, start_times, laws, valid, periods = (
        [] for i in range(8)
    )
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
                    start_times[i_ctl][i_daytype].append(
                        float(ctl[idx + 6][1].split(" ")[-1])
                    )
                    n_items = int(float(ctl[idx + 7][0]))
                    if n_items > 0:
                        ctl_data[i_ctl][i_daytype].append(
                            space_data_to_list(ctl[idx + 8], "float")
                        )
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


def weather(file_path):
    """Read ESP-r ascii weather file.

    col 1: Diffuse solar on the horizontal (W/m^2)
    col 2: External dry bulb temperature   (Tenths °C)
    col 3: Direct normal solar intensity   (W/m^2)
    col 4: Prevailing wind speed           (Tenths m/s)
    col 5: Wind direction                  (clockwise ° from north)
    col 6: Relative humidity               (%)

    """
    solar_diff = []
    temp_db = []
    solar_direct = []
    wind_speed = []
    wind_direction = []
    humidity_relative = []
    header_lines = 13
    with open(file_path, "r") as csvfile:
        data = csv.reader(csvfile, delimiter=",")
        for _ in range(header_lines):
            next(data, None)
        i = 0
        for row in data:
            if (i % 25) != 24:
                solar_diff.append(float(row[0]))
                temp_db.append(float(row[1]) / 10.0)
                solar_direct.append(float(row[2]))
                wind_speed.append(float(row[3]) / 10.0)
                wind_direction.append(float(row[4]))
                humidity_relative.append(float(row[5]))
            i += 1
    return {
        "solar_diff": solar_diff,
        "temp_db": temp_db,
        "solar_direct": solar_direct,
        "wind_speed": wind_speed,
        "wind_direction": wind_direction,
        "humidity_relative": humidity_relative,
    }


def weather_v2(file_path):
    """Read ESP-r ascii weather file.
    """
    solar_diff = []
    temp_db = []
    solar_direct = []
    wind_speed = []
    wind_direction = []
    humidity_relative = []
    header_lines = 15
    with open(file_path, "r") as csvfile:
        data = csv.reader(csvfile, delimiter=",")
        for _ in range(header_lines):
            next(data, None)
        i = 0
        for row in data:
            if (i % 25) != 24:
                solar_diff.append(float(row[1]))
                temp_db.append(float(row[0]) / 10.0)
                solar_direct.append(float(row[2]))
                wind_speed.append(float(row[3]) / 10.0)
                wind_direction.append(float(row[4]))
                humidity_relative.append(float(row[5]))
            i += 1
    return {
        "solar_diff": solar_diff,
        "temp_db": temp_db,
        "solar_direct": solar_direct,
        "wind_speed": wind_speed,
        "wind_direction": wind_direction,
        "humidity_relative": humidity_relative,
    }

    
def zone_to_predef_entity(geo_file, name, desc, category):
    """Convert a zone geometry file to a predefined entity entry.

    Args:
        geo_file: ESP-r geometry file.

    Returns:
        A text file that can be copied into an ESP-r predefined entities
        database.
    """
    # TODO(j.allison): Process visual entities
    # TODO(j.allison): Shift x,y,z to (0,0,0) origin

    geo = geometry(geo_file)
    all_vertices = geo["vertices"]
    props = geo["props"]
    surfaces = geo["edges"]
    vx = [v[0] for v in all_vertices]
    vy = [v[1] for v in all_vertices]
    vz = [v[2] for v in all_vertices]
    size = (max(vx) - min(vx), max(vy) - min(vy), max(vz) - min(vz))

    out_file = f"{name}.txt"
    with open(out_file, "w+") as the_file:
        the_file.write(f"*item,{name},{desc} # tag name menu entry\n")
        the_file.write(f"*incat,{category}           \n")
        the_file.write("*sourced,Custom built.\n")
        the_file.write("*origin,0.0,0.0,0.0  # local origin\n")
        the_file.write(
            f"*bounding_box,  {size[0]:.3f}  {size[1]:.3f}  {size[2]:.3f}  # extents of object\n"
        )
        the_file.write("*Text\n")
        the_file.write(f"{desc}\n")
        the_file.write("*End_text\n")
        the_file.write("#\n")
        for i, vertex in enumerate(all_vertices):
            the_file.write(
                f"*vertex,{vertex[0]:.5f},{vertex[1]:.5f},{vertex[2]:.5f}  #   {i + 1}\n"
            )
        the_file.write("#\n")
        for i, (s, p) in enumerate(zip(surfaces, props)):
            the_file.write(
                f"*mass,{p[0]},{p[5]},OPAQUE,{len(s)},"
                + "  ".join(map(str, s))
                + f"  #   {i + 1}\n"
            )
        the_file.write("#\n")
        # the_file.write(f"*vobject,{name},{desc},{len(self.vis)},{','.join([v[8] for v in self.vis])}")
        the_file.write("*end_item")
