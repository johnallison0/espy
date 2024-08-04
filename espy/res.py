"""Module to automate retrieval of data from res."""
import csv
import itertools
import os
from subprocess import PIPE, run

import pandas

from espy import get
from espy.utils import dtparse_espr

res_dict = {
    # Climate
    "Ambient temperature": ["a", "a",'-'],
    "Solar Dir N": ["a", "b",'-'],
    "Solar diffuse": ["a", "c",'-'],
    "Wind speed": ["a", "d",'-'],
    "Wind direction": ["a", "e",'-'],
    "Ambient RH": ["a", "f",'-'],
    "Sky illuminance": ["a", "g",'-'],
    # Temperatures
    "Zone db T": ["b", "a", "-"],
    "Zone db T - ambient db T": ["b", "b", "-"],
    "Zone db T - other zone db T": ["b", "c", "-"],
    "Zone control point T": ["b", "d", "-"],
    "Zone Resultant T": ["b", "e", "-"],
    "Mean Radiant T (area wtd)": ["b", "f", "-"],
    "Mean Radiant T (at sensor)": ["b", "g", "-"],
    "Dew point T": ["b", "h", "-"],
    "Surf inside face T": ["b", "i", "-"],
    "Surf T - dewpoint T": ["b", "j", "-"],
    "Surf outside face T": ["b", "k", "-"],
    "Surf node T": ["b", "l", "-"],
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
    "Solar entering from outside": ["d", "a"],
    "Solar entering from adj": ["d", "b"],
    "Solar absorbed in zone": ["d", "c"],
    # Zone flux
    "Infiltration (from outside)": ["f", "a"],
    "Ventilation (adj zones)": ["f", "b"],
    "Occupant casual gains (R+C)": ["f", "c"],
    "Lighting casual gains (R+C)": ["f", "d"],
    "Small power casual gains (R+C)": ["f", "e"],
    "Other casual gains (R+C)": ["f", "f"],
    "Controlled casual gains (R+C": ["f", "g"],
    "Opaq surf conv @extrn": ["f", "h"],
    "Opaq surf conv @partns": ["f", "i"],
    "Tran surf conv @extrn": ["f", "j"],
    "Tran surf conv @partns": ["f", "k"],
    "Total surface conv": ["f", "l"],
    # Surface flux
    "conduction (inside)": ["g", "a", "-", "N"],
    "convection (inside)": ["g", "b", "-", "N"],
    # Heat/cool/humidify
    "Sensible heating load": ["h", "a"],
    "Sensible cooling load": ["h", "b"],
    "Dehumidification load": ["h", "c"],
    "Humidification load": ["h", "d"],
    "Sensible H+C loads": ["h", "e"],
    "Latent H+C loads": ["h", "f"],
    "All Sensible + latent load": ["h", "g"],
    "Aggregate heating load": ["h", "h"],
    "Aggregate cooling load": ["h", "i"],
    "Aggregate dehumidification": ["h", "j"],
    "Aggregate humidification": ["h", "k"],
    # Zone RH
    "Zone RH": ["i"],
    # Casual gains (more to complete)
    "occupant convective": ["j", "f", "-"],
    "lighting convective": ["j", "j", "-"],
    "equipment convective": ["j", "n", "-"],
}

time_dict = {"Julian": ["*", "a"], "DateTime": ["*", "a", "*", "a"]}


def calc_airtightness(res_file, mfr_file, volume, zones):
    """Calculate building airtightness at 50 Pa.

    Args:
        res_file: ESP-r results database.
        mfr_file: ESP-r mass flow results database.
        volume: Heated volume of building (m^3).
        zones: List of strings with zones to include e.g.
            zones = ["a", "b"] to get air flow from those air flow nodes

    Returns:
        n_50: Air change rate (1/h)
        q_50: Air permeability (m^3/(h.m^2))
        w_50: Specific leakage rate (m^3/(h.m^2))
    """

    # Get volume flow rate from ambient
    cmd_1 = [
        "",  # confirm building results file
        "c",  # reports
        "g",  # performance metrics
        ">",  # open file
        "temp.csv",
        "",
        "n",  # network flow
        mfr_file,
        "j",  # volume flow rate
        "a",  # in m^3/s
        "d",  # total from ambient
    ]

    cmd_write = ["-", "!", ">", "-", "-", "-", "-"]

    cmd = cmd_1 + zones + cmd_write
    cmd = "\n".join(cmd)
    run(["res", "-file", res_file, "-mode", "script"], input=cmd, encoding="ascii")
    vdot_ambient = []
    with open("temp.csv", "r") as f_in:
        for i, line in enumerate(f_in):
            if i > 2:
                vdot_ambient.append([float(x) for x in line.strip().split()[0::2][1:]])
    air_changes_build = [3600 * sum(x) / volume for x in vdot_ambient]
    n_50 = sum(air_changes_build) / len(air_changes_build)

    return n_50


def air_supply(res_file, mfr_file, zones):
    """Retreive air supply from ambient to zones.

    Args:
        res_file: ESP-r results database.
        mfr_file: ESP-r mass flow results database.
        zones: List of strings with zones to include e.g.
            zones = ["a", "b"] to get air flow from those air flow nodes

    Returns:
        df: Pandas dataframe with volume flow rate to/from ambient per zone.
    """

    # Get volume flow rate from ambient
    cmd_1 = [
        "",  # confirm building results file
        "c",  # reports
        "g",  # performance metrics
        "^",  # delim
        "e",  # comma
        "*",
        "a",
        "*",
        "a",  # Time mm-dd 10:30:00
        ">",  # open file
        "temp.csv",
        "",
        "n",  # network flow
        mfr_file,
        "j",  # volume flow rate
        "a",  # in m^3/s
        "d",  # total from ambient
    ]

    cmd_write = ["-", "!", ">", "-", "-", "-", "-"]

    cmd = cmd_1 + zones + cmd_write
    cmd = "\n".join(cmd)
    run(["res", "-file", res_file, "-mode", "script"], input=cmd, encoding="ascii")

    header_lines = 3
    with open("temp.csv", "r") as infile, open(
        "airflow.csv", "w", newline=""
    ) as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        line_count = 1
        for row in reader:
            if line_count < header_lines:
                pass
            elif line_count == header_lines:
                newrow = row[0].strip().split()
                writer.writerow(newrow)
            else:
                newrow = row
                writer.writerow(newrow)
            line_count += 1
    os.remove("temp.csv")

    df = pandas.read_csv("airflow.csv", sep=",", header=0, index_col=0)

    return df


def time_series(cfg_file, res_file, param_list, out_file=None, time_fmt='DateTime'):
    """Extract results from results database.

    Arguments
        cfg_file: string
            ESP-r configuration file..
        res_file: string
            ESP-r results database
        param_list: list
            parameters to extract
            Examples -
                param_list = [['all', 'Zone db T']]
                param_list = [['id:reception', 'Zone db T']]
                param_list = [[['id:roof_space', 'id:reception'], 'Zone db T']]
                param_list = [[[1, 2], 'Zone db T'], [['id:reception', 'b'], 'Wind direction']]
        out_file: string; default None
            name of exported CSV file
        time_fmt: str; default 'DateTime'
            format of datetime in exported CSV
            'Julian' or 'DateTime'

    Returns
        pandas.DataFrame 
            extracted results
    """

    # Read cfg file for list of zones
    cfg = get.config(cfg_file)
    zones = cfg["zones"]

    # Loop through each zone file and get zone name
    zone_names = []
    for ind, _ in enumerate(zones):
        file_path = zones[ind][1]["geo"]
        zone_names.append(get.geometry(file_path)["name"])

    # TODO(j.allison): Check/validate time_fmt
    res_open = ["", "c"]
    if time_fmt:
        csv_open = [">", "temp.csv", "desc"] + time_dict[time_fmt] + ["&", "^", "e"]
    else:
        csv_open = [">", "temp.csv", "desc"] + ["&", "^", "e"]
    perf_met = ["g"]

    res_select = []
    for item in param_list:
        zone_select = []
        zone_input = item[0]
        metric_input = item[1]
        # ---------------------------------
        # Select all zones
        # ---------------------------------
        if zone_input == "all":
            # res_select.append(["4", "*", "-"])
            res_select.append(["4", "*"])
        # ---------------------------------
        # Multiple zone selections
        # ---------------------------------
        elif isinstance(zone_input, list) and len(zone_input) > 1:
            for j in zone_input:
                # Selection by zone number.
                if isinstance(j, int):
                    zone_select.append(str(j))
                # Selection by zone name.
                elif j[:3] == "id:":
                    selected_zone = j[3:]
                    chr_zone = [
                        # chr(96 + ind + 1)
                        str(ind + 1)
                        for ind, x in enumerate(zone_names)
                        if x == selected_zone
                    ]
                    # If exists select it, otherwise throw error
                    if chr_zone:
                        zone_select.append(chr_zone[0])
                    else:
                        print(
                            "zone selection error, '{}' not found".format(selected_zone)
                        )
                else:
                    print("zone selection error for '{}', check input format".format(j))
            # res_select.append(["4"] + zone_select + ["-"])
            n = len(zone_select)
            if n:
                res_select.append(["4",'<'] + [str(n)] + zone_select)
            else:
                print('no zones selected')
                return None
        # ---------------------------------
        # Single selection
        # ---------------------------------
        # From zone name
        elif isinstance(zone_input, str) and zone_input[:3] == "id:":
            selected_zone = zone_input[3:]
            chr_zone = [
                # chr(96 + ind + 1)
                str(ind + 1)
                for ind, x in enumerate(zone_names)
                if x == selected_zone
            ]
            # If exists select it, otherwise throw error
            if chr_zone:
                zone_select.append(chr_zone[0])
            else:
                print("zone selection error, '{}' not found".format(selected_zone))
            n = len(zone_select)
            if n:
                res_select.append(["4",'<'] + [str(n)] + zone_select)
            else:
                print('no zones selected')
                return None
        # Assume single letter selection
        elif isinstance(zone_input, int):
            zone_select.append(str(zone_input))
            res_select.append(["4",'<'] + [str(n)] + zone_select)
        else:
            print(
                "zone selection error for '{}', check input format".format(zone_input)
            )            

        # Select metric.
        # If error in single selection, gets all zones (for now)
        res_select.append(res_dict[metric_input])
        # Surface flux
        if res_dict[metric_input][0] == "g":
            surface_input = item[2]
            res_select.append(surface_input + ["-"])

    # Flatten list
    res_select = list(itertools.chain.from_iterable(res_select))

    csv_close = ["!", ">"]
    res_close = ["-", "-", "-", "-"]

    cmd = res_open + csv_open + perf_met + res_select + csv_close + res_close
    cmd = "\n".join(cmd)
    # print(cmd)
    res = run(
        ["res", "-file", res_file, "-mode", "script"],
        input=cmd,
        stdout=PIPE,
        stderr=PIPE,
        encoding="ascii",
    )
    # print(res.stdout)

    header_lines = 4
    if out_file:
        with open("temp.csv", "r") as infile, open(out_file, "w", newline="") as outfile:
            reader = csv.reader(infile)
            writer = csv.writer(outfile)
            line_count = 1
            for row in reader:
                if line_count < header_lines:
                    pass
                elif line_count == header_lines:
                    newrow = ["Time"] + row[1:]
                    writer.writerow(newrow)
                else:
                    newrow = row
                    writer.writerow(newrow)
                line_count += 1

    # if time_fmt == 'DateTime':
    #     data_frame = pandas.read_csv(
    #         "temp.csv", sep=",", header=3, index_col=0,
    #         parse_dates=True, date_parser=dtparse_espr
    #     )
    # else:
    data_frame = pandas.read_csv(
        "temp.csv",
        sep=",",
        header=3,
        index_col=0,
        parse_dates=True,
        infer_datetime_format=True)
    os.remove("temp.csv")

    return data_frame


def abovebelow(cfg_file, res_file, param_list, is_below=False, out_file=None, query_point=25.):
    """Get hours above or below a value.
    
    Arguments
        cfg_file: str
            ESP-r configuration file
        res_file: str
            ESP-r results database
        param_list: list
            parameters to extract
            Examples
                param_list = ['all', 'Zone db T']
                param_list = ['id:reception', 'Zone db T']
                param_list = [['id:roof_space', 'id:reception'], 'Zone db T']
                param_list = [[1, 2], 'Zone db T']
        out_file: str; default None
            name of exported CSV file
        query_point: float; default 25
            value to fetch values above or below

    Returns
        list, list
            [[zone_name, hours_outside, percent_outside], ...]

    """

    # Read cfg file for list of zones
    cfg = get.config(cfg_file)
    zones = cfg["zones"]

    # Loop through each zone file and get zone name
    zone_names = []
    for ind, _ in enumerate(zones):
        file_path = zones[ind][1]["geo"]
        zone_names.append(get.geometry(file_path)["name"])

    # TODO(j.allison): Check/validate time_fmt
    res_open = ["", "d"]
    csv_open = [">", "temp.csv", "", "^", "e", "d" if is_below else "c"]
        

    res_select = []
    zone_select = []
    zone_input = param_list[0]
    metric_input = param_list[1]
    # ---------------------------------
    # Select all zones
    # ---------------------------------
    if zone_input == "all":
        num_zones = len(zones)
        # res_select.append(["4", "*", "-"])
        res_select.append(["4", "*"])
    # ---------------------------------
    # Multiple zone selections
    # ---------------------------------
    elif isinstance(zone_input, list):
        num_zones = len(zone_input)
        for j in zone_input:
            # Selection by zone number.
            if isinstance(j, int):
                zone_select.append(str(j))
            # Selection by zone name.
            elif j[:3] == "id:":
                selected_zone = j[3:]
                chr_zone = [
                    # chr(96 + ind + 1)
                    str(ind + 1)
                    for ind, x in enumerate(zone_names)
                    if x == selected_zone
                ]
                # If exists select it, otherwise throw error
                if chr_zone:
                    zone_select.append(chr_zone[0])
                else:
                    print(
                        "zone selection error, '{}' not found".format(selected_zone)
                    )
            else:
                print("zone selection error for '{}', check input format".format(j))
        n = len(zone_select)
        if n:
            res_select.append(["4",'<'] + [str(n)] + zone_select)
        else:
            print('no zones selected')
            return None
    # ---------------------------------
    # Single selection
    # ---------------------------------
    # From zone name
    elif isinstance(zone_input, str) and zone_input[:3] == "id:":
        num_zones = 1
        selected_zone = zone_input[3:]
        chr_zone = [
            # chr(96 + ind + 1)
            str(ind + 1)
            for ind, x in enumerate(zone_names)
            if x == selected_zone
        ]
        # If exists select it, otherwise throw error
        if chr_zone:
            zone_select.append(chr_zone[0])
        else:
            print("zone selection error, '{}' not found".format(selected_zone))
        n = len(zone_select)
        if n:
            res_select.append(["4",'<'] + [str(n)] + zone_select)
        else:
            print('no zones selected')
            return None
    # Assume single letter selection
    elif isinstance(zone_input, int):
        num_zones = 1
        zone_select.append(str(zone_input))
        res_select.append(["4",'<'] + [str(n)] + zone_select)
    else:
        print(
            "zone selection error for '{}', check input format".format(zone_input)
        )            

    # Select metric.
    # If error in single selection, gets all zones (for now)
    res_select.append(res_dict[metric_input])
    # Surface flux
    if res_dict[metric_input][0] == "g":
        surface_input = param_list[2]
        res_select.append(surface_input + ["-"])

    # Flatten list
    res_select = list(itertools.chain.from_iterable(res_select))

    res_close = [">", "-", "-"]

    cmd = res_open + csv_open + res_select + [str(query_point)] + res_close
    cmd = "\n".join(cmd)
    # print(cmd)
    res = run(
        ["res", "-file", res_file, "-mode", "script"],
        input=cmd,
        stdout=PIPE,
        stderr=PIPE,
        encoding="ascii",
    )
    # print(res.stdout)

    # Read in CSV output from ESP-r
    data = []
    header = 9
    with open("temp.csv", "r") as file:
        reader = csv.reader(file, delimiter=",")
        line_count = 1
        for row in reader:
            if line_count < header:
                # skipping header
                line_count += 1
            elif line_count >= header + num_zones:
                break
            else:
                data.append(row)
                line_count += 1
    # print(data)

    # Remove temporary CSV file.
    # Handle errors while calling os.remove()
    try:
        os.remove("temp.csv")
    except FileNotFoundError:
        print("Error while deleting file ", "temp.csv")

    # Calculate total number of hours
    total_hours = float(data[0][6]) + float(data[0][7])

    # Write data to output list
    idx_metric = 7 if is_below else 6
    output = []
    for row in data:
        output.append([
            row[0],
            float(row[idx_metric]),
            round(float(row[idx_metric]) / total_hours * 100, 1)])

    # Write back out to CSV
    if out_file:
        if is_below:
            header_comment = [f"# Underheating (<{query_point} °C) metrics per zone."]
        else:
            header_comment = [f"# Overheating (>{query_point} °C) metrics per zone."]
        headers = ["Zone", "Time (h)", "Frequency (%)"]
        with open(out_file, "w", newline="") as write_file:
            writer = csv.writer(write_file)
            writer.writerow(header_comment)
            writer.writerow(headers)
            for row in output:
                writer.writerow(row)

    return output


def energy_balance(cfg_file, res_file, out_file=None, group=None):
    """Get zone energy balance."""
    # Read cfg file for list of zones
    cfg = get.config(cfg_file)
    zones = cfg["zones"]

    # Get zone energy balance from ESP-r to temporary file
    cmd_open = ["", "d", ">", "temp.csv", "", "^", "e"]
    if group:
        cmd_group = ["4", "!", group, "-"]
    else:
        cmd_group = []
    cmd_zone_bal = ["h", "b", "b", ">", "-", "-"]
    cmd = "\n".join(cmd_open + cmd_group + cmd_zone_bal)
    run(
        ["res", "-file", res_file, "-mode", "script"],
        stdout=PIPE,
        input=cmd,
        encoding="ascii",
        check=True,
    )

    # Read CSV from ESP-r
    data = []
    for i in range(len(zones)):
        with open("temp.csv", "r") as file:
            reader = csv.reader(file, delimiter=",")
            data.append(
                [
                    row
                    for idx, row in enumerate(reader)
                    if idx in range(19 * i + 6, 19 * i + 21)
                ]
            )

    # remove temporary CSV file
    # Handle errors while calling os.remove()
    try:
        os.remove("temp.csv")
    except:
        print("Error while deleting file ", "temp.csv")

    # Restructure data for HighCharts
    # Assume all headers in first zone. If no plant input/extract this will not work
    # for the last two items
    headers = ["Stack"] + [x[0].strip() for x in data[0]]
    zone_gains = []
    zone_losses = []
    for zone in data:
        # ESP-r bug: 'Convection @ transp surf' written out as 'No plant input/extract'
        # when there is 'No plant input/extract' i.e. zone[12] will be length 1.
        # Also, when 'No plant input/extract' i.e. zone[13] will be length 1.
        zone_gains.append([float(x[1]) if len(x) == 3 else 0 for x in zone])
        zone_losses.append([float(x[2]) if len(x) == 3 else 0 for x in zone])

    # If taking a subset of all the zones (i.e. via groups), then remove the empty results
    zone_gains = [x for x in zone_gains if x != []]
    zone_losses = [x for x in zone_losses if x != []]

    # Sum across all zones
    total_gains = ["Gain"] + [round(sum(x), 1) for x in zip(*zone_gains)]
    total_losses = ["Loss"] + [abs(round(sum(x), 1)) for x in zip(*zone_losses)]

    # Export to HighCharts CSV format if given out_file
    if out_file is not None:
        with open(out_file, "w", newline="") as write_file:
            writer = csv.writer(write_file)
            writer.writerow(headers[0:-1])
            writer.writerow(total_gains[0:-1])
            writer.writerow(total_losses[0:-1])

    return [headers[1:], total_gains[1:], total_losses[1:], zone_gains, zone_losses]


def get_pv(res_file, elr_file, out_file=None):
    """Get PV output."""
    cmd = [
        "",
        "g",
        elr_file,
        "b",
        ">",
        out_file,
        "^",
        "e",
        "*",
        "a",
        "c",
        "b",
        "-",
        "!",
        ">",
        "-",
        "-",
        "-",
    ]
    cmd = "\n".join(cmd)
    run(
        ["res", "-file", res_file, "-mode", "script"],
        stdout=PIPE,
        stderr=PIPE,
        input=cmd,
        encoding="ascii",
        check=True,
    )


def running_mean(data, alpha=0.8, daily=True):
    """Compute exponentially weighted running mean.

    Formula taken from BS EN 15251 eqn 2.

    Note that the first value in the input data is taken as the first
    running mean. This means that roughly the first 7 returned values
    cannot be considered a true running mean.
    
    Arguments
        data: pandas.Series
            input data
        alpha: float
            weighting factor
            0. - 1.
            optional, default 0.8
        daily: boolean
            if True, computes running mean of daily average
            assumes that series labels are DateTime
            otherwise, operates on input data as-is
            optional, default True

    Returns
        running_mean: pandas.Series
            computed running mean, with the same indices as input data

    Example
        df = time_series('model.cfg','results.res',[['all','Ambient temperature']])
        rm = running_mean(df['Ambientdb(C)(C)'])
    """

    # Initialise running_mean with same indices and values as data.
    # Values should all be overwritten.
    running_mean = data

    # If daily, compute daily average.
    if daily:
        x = data.groupby(lambda x: pandas.to_datetime(x).date).agg('mean')
    else:
        x = data

    # Set first value.
    if daily:
        i = pandas.to_datetime(data.index).date == x.index[0]
    else:
        i = 0
    prevx = x[0]
    prevrm = prevx
    running_mean[i] = prevx

    # Set subsequent values.
    for ix,xx in enumerate(x):
        if daily:
            i = pandas.to_datetime(data.index).date == x.index[ix]
        else:
            i = ix
        v = (1.-alpha) * prevx + alpha * prevrm
        running_mean[i] = v
        prevx = xx
        prevrm = v

    return running_mean


def add_BS15251_comfort(data,category=2):
    """Adds BS EN 15251:2007 comfort limits to dataframe.

    Uses criteria for non-mechanically cooled residential buildings,
    as described in Annexes A.1 and A.2, using recommended values in
    Table A.2 when outside the valid temperature range for adaptive
    criteria. Note that there is no upper temperature for residential
    circulation zones, so the temperature for living is used in this
    case.
    
    Assumes that data contains a column called 'Ambientdb(C)(C)', as 
    would be output from time_series. Raises exception if not.

    Adds four new columns into data, called:
    'livingUpperComfort'
    'livingLowerComfort'
    'otherUpperComfort'
    'otherLowerComfort'

    Arguments
        data: pandas.DataFrame
            time step data including ambient temperature
        category: int, default 2
            comfort category as in BS EN 15251:2007 Table 1

    Returns
        none (modifies data in-place)

    Example
        df = time_series('model.cfg','results.res',[
            [['liv','hall'],'Zone Resultant T'],
            ['all','Ambient temperature']])
        add_BS15251_comfort(df)
        liv_overheating_mask = df['livResT(C)']-df['livingUpperComfort'] > 0
        liv_underheating_mask = df['livResT(C)']-df['livingLowerComfort'] < 0
        hall_overheating_mask = df['hallResT(C)']-df['otherUpperComfort'] > 0
        hall_underheating_mask = df['hallResT(C)']-df['otherLowerComfort'] < 0
    """

    if category == 1:
        v = 2
        ll = 21.
        lu = 25.5
        ol = 18.
        ou = lu
    elif category == 2:
        v = 3
        ll = 20.
        lu = 26.
        ol = 16.
        ou = lu
    elif category ==3:
        v = 4
        ll = 18.
        lu = 27.
        ol = 14.
        ou = lu
    else:
        print('Invalid category')
        return
    rm = running_mean(data['Ambientdb(C)(C)'])
    data['livingUpperComfort'] = [lu if x<10 else 0.33*x+18+v for x in rm]
    data['livingLowerComfort'] = [ll if x<15 else 0.33*x+18-v for x in rm]
    data['otherUpperComfort'] = [ou if x<10 else 0.33*x+18+v for x in rm]
    data['otherLowerComfort'] = [ol if x<15 else 0.33*x+18-v for x in rm]

    



    
