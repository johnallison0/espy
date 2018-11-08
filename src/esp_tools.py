from subprocess import run, PIPE
import itertools


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


def res_get(res_file, out_file, param_list, time_fmt):
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

    res_open = ['', 'c']
    time_dict = {'Julian': ['*', 'a'], 'DateTime': ['*', 'a', '*', 'a']}
    csv_open = ['>', out_file, 'desc'] + time_dict[time_fmt] + ['&', '^', 'e']
    perf_met = ['g']

    res_select = []
    for i, item in enumerate(param_list):
        # Select zones
        if (item[0] == 'all'):
            res_select.append(['4', '*', '-'])
        else:
            res_select.append(['4'] + item[0] + ['-'])
        # Select metric
        res_select.append(res_dict[item[1]])
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
