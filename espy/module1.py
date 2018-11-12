from subprocess import run, PIPE
import itertools
from datetime import datetime


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
        for cnt, line in enumerate(fp):
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


def _get_var(ifile, str):
    y = [x[1] for x in ifile if x[0] == str]
    if y:
        var = y[0]
    else:
        var = None

    return var


def read_cfg(filepath):
    """
    Reads in an ESP-r configuration file.
    """
    cfg = _read_file(filepath)

    # Modified date
    date = _get_var(cfg, '*date')  # string
    date = datetime.strptime(date, "%a %b %d %H:%M:%S %Y")  # datetime

    # Build dictionary of model paths
    paths = {
        'zones': _get_var(cfg, '*zonpth'),
        'networks': _get_var(cfg, '*netpth'),
        'controls': _get_var(cfg, '*ctlpth'),
        'aim': _get_var(cfg, '*aimpth'),
        'radiance': _get_var(cfg, '*radpth'),
        'images': _get_var(cfg, '*imgpth'),
        'documents': _get_var(cfg, '*docpth'),
        'databases': _get_var(cfg, '*dbspth'),
        'hvac': _get_var(cfg, '*hvacpth'),
        'BASESIMP': _get_var(cfg, '*bsmpth')
    }

    # Build dictionary of model databases
    databases = {
        'material': _get_var(cfg, '*stdmat'),
        'cfc': _get_var(cfg, '*stdcfcdb'),
        'mlc': _get_var(cfg, '*stdmlc'),
        'optics': _get_var(cfg, '*stdopt'),
        'pressure': _get_var(cfg, '*stdprs'),
        'devn': _get_var(cfg, '*stdevn'),
        'climate': _get_var(cfg, '*stdclm'),
        'mscl': _get_var(cfg, '*stdmscldb'),
        'mould': _get_var(cfg, '*stdmould'),
        'plant': _get_var(cfg, '*stdpdb'),
        'sbem': _get_var(cfg, '*stdsbem'),
        'predef': _get_var(cfg, '*stdpredef')
    }

    # Control file
    ctl = _get_var(cfg, '*ctl')

    # Assessment year
    year = _get_var(cfg, '*year')

    # Get index numbers of list elements for begin of each zone desc.
    idx_zone_begin = [ind for ind, x in enumerate(cfg) if x[0] == '*zon']
    idx_zone_end = [ind for ind, x in enumerate(cfg) if x[0] == '*zend']
    n_zones = len(idx_zone_begin)

    # loop through each 'slide' of the cfg_file for the various zone files
    Z = []
    for i in range(n_zones):
        cfg_slice = cfg[idx_zone_begin[i]:idx_zone_end[i]]

        # Get zone no.
        iz_zone = _get_var(cfg_slice, '*zon')

        # Add files to dictionary
        iz_files = {
            'opr': _get_var(cfg_slice, '*opr'),
            'geo': _get_var(cfg_slice, '*geo'),
            'con': _get_var(cfg_slice, '*con'),
            'tmc': _get_var(cfg_slice, '*tmc')
        }

        # Append to list
        Z.append([int(iz_zone), iz_files])

    # If list is empty return NoneType
    if not Z:
        Z = None

    return cfg, date, paths, databases, ctl, year, Z


def read_geo(filepath):
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
    name = _get_var(geo, '*Geometry').split(',')[2]

    # Modified date
    date = _get_var(geo, '*date')  # string
    date = datetime.strptime(date, "%a %b %d %H:%M:%S %Y")  # datetime

    # Zone description
    desc = ' '.join(geo[2])

    # Need to re-split file to access items with comma following keyword
    file2 = []
    for x in geo:
        file_split = x[0].split(',', 1)
        if file_split:
            file2.append(file_split)

    # Scan through list and get vertices, surface edges and surface props
    V = []
    E = []
    S = []
    for x in file2:
        if x[0] == '*vertex':
            V.append([float(y) for y in x[1].split(',')])
        elif x[0] == '*edges':
            dat = x[1].split(',', 1)  # sep. no. of edges from list of vertices
            E.append([int(y) for y in dat[1].split(',')])
        elif x[0] == '*surf':
            S.append(x[1].split(','))

    return name, desc, date, V, E, S


def edit_material_prop(cfg_file, change_list):
    # This function will build the command list to edit material properties in
    # the materials db via prj.
    # NOTE: Edits are made in place with the existing database entires,
    # so backups/copies should be made before making changes.
    # TODO(j.allison): Do input and range checking

    # Open material database
    cmd_mat_open = ['b', 'c', 'a']

    # change_list is provided as a list of lists of the changes i.e.
    # change_list =
    # [['class_chr', 'material_chr', 'material_prop', value]]
    map_prop_dict = {
        'conductivity': 'c',
        'density': 'd',
        'specific heat': 'e',
        'emissivity out': 'f',
        'emissivity in': 'g',
        'absorptivity out': 'h',
        'absorptivity in': 'i',
        'vapour res': 'j'
    }
    n_changes = len(change_list)
    cmd_mat = []
    for i in range(n_changes):
        cmd_mat_i = [
            change_list[i][0], change_list[i][1],
            map_prop_dict[change_list[i][2]],
            str(change_list[i][3]), '-', 'Y', '-', 'Y', 'Y'
        ]
        cmd_mat.append(cmd_mat_i)
    # Flatten list
    cmd_mat = list(itertools.chain.from_iterable(cmd_mat))

    # Exit database maintenance, update mode name list and rebuild
    # existing zone construction files
    cmd_mat_close = ['-', '-', 'Y', 'Y', '-']

    # Concatenate list of commands
    cmd = cmd_mat_open + cmd_mat + cmd_mat_close
    cmd = '\n'.join(cmd)
    prj = run(['prj', '-file', cfg_file, '-mode', 'script'],
              stdout=PIPE,
              input=cmd,
              encoding='ascii')
    return prj


def edit_layer_thickness(cfg_file, change_list):
    # This function will build the command list to edit the layer thickness in
    # the MLC db via prj.
    # NOTE: Edits are made in place with the existing database entires,
    # so backups/copies should be made before making changes.
    # TODO(j.allison): Do input and range checking

    # Open construction database
    cmd_con_open = ['b', 'e', 'a']

    # change_list is provided as a list of lists of the changes i.e.
    # change_list =
    # [['class_chr', 'construction_chr', layer_no, layer_thickness]]
    menu_offset = 11  # letter start offset
    n_changes = len(change_list)
    cmd_con = []
    for i in range(n_changes):
        layer_no_alpha = chr(96 + menu_offset + change_list[i][2])
        if (change_list[i][3] > 300):
            cmd_con_i = [
                change_list[i][0], change_list[i][1], layer_no_alpha, 'N',
                str(change_list[i][3]), 'Y', '-', '-', 'Y', 'Y'
            ]
            print('The input value for layer thickness in mm ({}) should be '
                  'less than 300.'.format(change_list[i][3]))
            print('Layer has been updated regardless.')
        else:
            cmd_con_i = [
                change_list[i][0], change_list[i][1], layer_no_alpha, 'N',
                str(change_list[i][3]), '-', '-', 'Y', 'Y'
            ]
        cmd_con.append(cmd_con_i)
    # Flatten list
    cmd_con = list(itertools.chain.from_iterable(cmd_con))

    # Exit database maintenance, update mode name list and rebuild
    # existing zone construction files
    cmd_con_close = ['-', '-', '-', 'Y', 'Y', '-']

    # Concatenate list of commands
    cmd = cmd_con_open + cmd_con + cmd_con_close
    cmd = '\n'.join(cmd)
    prj = run(['prj', '-file', cfg_file, '-mode', 'script'],
              stdout=PIPE,
              input=cmd,
              encoding='ascii')
    return prj


def run_sim(cfg_file, res_file, sim_start_d, sim_start_m, sim_end_d, sim_end_m,
            start_up_d, tsph, integrate):
    # Only designed to work for models without additional networks eg. massflow
    cmd = [
        '', 'c', res_file,
        '{} {}'.format(sim_start_d, sim_start_m), '{} {}'.format(
            sim_end_d, sim_end_m), '{}'.format(start_up_d), '{}'.format(tsph),
        integrate, 's', 'Y', 'description', 'Y', 'Y', '-', '-'
    ]
    cmd = '\n'.join(cmd)
    bps = run(['bps', '-file', cfg_file, '-mode', 'script'],
              stdout=PIPE,
              input=cmd,
              encoding='ascii')
    return bps


def gen_qa_report(cfg_file, filename):
    cmd = ['m', 'u', 'Y', '>', '../doc/' + filename, '!', '-', '-', '-']
    cmd = '\n'.join(cmd)
    prj = run(['prj', '-file', cfg_file, '-mode', 'script'],
              stdout=PIPE,
              input=cmd,
              encoding='ascii')
    return prj


def res_get(cfg_file, res_file, out_file, param_list, time_fmt):
    res_dict = {
        # Climate
        'Ambient temperature': ['a', 'a'],
        'Solar Dir N': ['a', 'b'],
        'Solar diffuse': ['a', 'c'],
        'Wind speed': ['a', 'd'],
        'Wind direction': ['a', 'e'],
        'Ambient RH': ['a', 'f'],
        'Sky illuminance': ['a', 'g'],
        # Temperatures
        'Zone db T': ['b', 'a'],
        'Zone db T - ambient db T': ['b', 'b'],
        'Zone db T - other zone db T': ['b', 'c'],
        'Zone control point T': ['b', 'd'],
        'Zone Resultant T': ['b', 'e'],
        'Mean Radiant T (area wtd)': ['b', 'f'],
        'Mean Radiant T (at sensor)': ['b', 'g'],
        'Dew point T': ['b', 'h'],
        'Surf inside face T': ['b', 'i'],
        'Surf T - dewpoint T': ['b', 'j'],
        'Surf outside face T': ['b', 'k'],
        'Surf node T': ['b', 'l'],
        # Comfort metrics
        # <TBC> requires extra inputs from user
        # 'Predicted Mean Vote (PMV)': ['c', 'a'],
        # 'PMV using SET': ['c', 'b'],
        # 'Percentage Dissatisfied (PPD)': ['c', 'c'],
        # 'Local delta T head-foot': ['c', 'd'],
        # 'Dissatisfied due to floor T': ['c', 'e'],
        # 'Diss. warm/ cool ceiling': ['c', 'f'],
        # 'Diss. wall rad T assymetry': ['c', 'g'],
        # 'Dissatisfied due to draught': ['c', 'h'],
        # Solar processes
        'Solar entering from outside': ['d', 'a'],
        'Solar entering from adj': ['d', 'b'],
        'Solar absorbed in zone': ['d', 'c'],
        # Zone flux
        'Infiltration (from outside)': ['f', 'a'],
        'Ventilation (adj zones)': ['f', 'b'],
        'Occupant casual gains (R+C)': ['f', 'c'],
        'Lighting casual gains (R+C)': ['f', 'd'],
        'Small power casual gains (R+C)': ['f', 'e'],
        'Other casual gains (R+C)': ['f', 'f'],
        'Controlled casual gains (R+C': ['f', 'g'],
        'Opaq surf conv @extrn': ['f', 'h'],
        'Opaq surf conv @partns': ['f', 'i'],
        'Tran surf conv @extrn': ['f', 'j'],
        'Tran surf conv @partns': ['f', 'k'],
        'Total surface conv': ['f', 'l'],
        # Surface flux
        # <TBC> requires extra inputs from user
        # Heat/cool/humidify
        'Sensible heating load': ['h', 'a'],
        'Sensible cooling load': ['h', 'b'],
        'Dehumidification load': ['h', 'c'],
        'Humidification load': ['h', 'd'],
        'Sensible H+C loads': ['h', 'e'],
        'Latent H+C loads': ['h', 'f'],
        'All Sensible + latent load': ['h', 'g'],
        'Aggregate heating load': ['h', 'h'],
        'Aggregate cooling load': ['h', 'i'],
        'Aggregate dehumidification': ['h', 'j'],
        'Aggregate humidification': ['h', 'k'],
    }

    # Read cfg file for list of zones
    cfg, date, paths, databases, ctl, year, zones = read_cfg(cfg_file)

    # Loop through each zone file and get zone name
    zone_names = []
    for ind, x in enumerate(zones):
        zone_names.append(read_geo(zones[ind][1]['geo'])[0])

    res_open = ['', 'c']
    time_dict = {'Julian': ['*', 'a'], 'DateTime': ['*', 'a', '*', 'a']}
    csv_open = ['>', out_file, 'desc'] + time_dict[time_fmt] + ['&', '^', 'e']
    perf_met = ['g']

    res_select = []
    zone_select = []
    for i, item in enumerate(param_list):
        zone_input = item[0]
        metric_input = item[1]
        # ---------------------------------
        # Select all zones
        # ---------------------------------
        if (zone_input == 'all'):
            res_select.append(['4', '*', '-'])
        # ---------------------------------
        # Multiple zone selections
        # ---------------------------------
        elif (isinstance(zone_input, list) and len(zone_input) > 1):
            for j in zone_input:
                # Selection by id:
                if (j[:3] == 'id:'):
                    selected_zone = j[3:]
                    chr_zone = [
                        chr(96 + ind + 1) for ind, x in enumerate(zone_names)
                        if x == selected_zone
                    ]
                    # If exists select it, otherwise throw error
                    if chr_zone:
                        zone_select.append(chr_zone[0])
                    else:
                        print("zone selection error, '{}' not found".format(
                            selected_zone))
                # Assume direct letter selection of zones if len = 1
                elif (len(j) == 1):
                    zone_select.append(j[0])
                else:
                    print("zone selection error for '{}', check input format".
                          format(j))
            res_select.append(['4'] + zone_select + ['-'])
        # ---------------------------------
        # Single selection
        # ---------------------------------
        # From zone name
        elif (zone_input[:3] == 'id:'):
            selected_zone = zone_input[3:]
            chr_zone = [
                chr(96 + ind + 1) for ind, x in enumerate(zone_names)
                if x == selected_zone
            ]
            # If exists select it, otherwise throw error
            if chr_zone:
                zone_select.append(chr_zone[0])
                res_select.append(['4'] + zone_select + ['-'])
            else:
                print("zone selection error, '{}' not found".format(
                    selected_zone))
        # Assume single letter selection
        elif (len(zone_input) == 1):
            zone_select.append(zone_input[0])
            res_select.append(['4'] + zone_select + ['-'])
        else:
            print("zone selection error for '{}', check input format".format(
                zone_input))
        # Select metric
        # If error in single selection, gets all zones (for now)
        res_select.append(res_dict[metric_input])

    # Flatten list
    res_select = list(itertools.chain.from_iterable(res_select))

    csv_close = ['!', '>']
    res_close = ['-', '-', '-']

    cmd = res_open + csv_open + perf_met + res_select + csv_close + res_close
    cmd = '\n'.join(cmd)
    res = run(['res', '-file', res_file, '-mode', 'script'],
              stdout=PIPE,
              input=cmd,
              encoding='ascii')
    return res
