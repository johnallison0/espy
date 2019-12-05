"""Module to automate retrieval of data from res."""
import csv
import itertools
import os
from subprocess import PIPE, run

import pandas

from espy import get


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


def time_series(cfg_file, res_file, param_list, out_file=None, time_fmt=None):
    """Extract results from results database to CSV.

    Args:
        cfg_file: ESP-r configuration file.
        res_file: ESP-r results database.
        param_list: List of parameters to extract.
            Examples -
            param_list = [['all', 'Zone db T']]
            param_list = [['id:reception', 'Zone db T']]
            param_list = [[['id:roof_space', 'id:reception'], 'Zone db T']]
            param_list = [[['a', 'b'], 'Zone db T'], [['id:reception', 'b'], 'Wind direction']]
        out_file (optional): Name of exported CSV file.
        time_fmt: Format of DateTime in exported CSV. Julian or DateTime

    Returns:
        res: Console feedback from res.
    """
    res_dict = {
        # Climate
        "Ambient temperature": ["a", "a"],
        "Solar Dir N": ["a", "b"],
        "Solar diffuse": ["a", "c"],
        "Wind speed": ["a", "d"],
        "Wind direction": ["a", "e"],
        "Ambient RH": ["a", "f"],
        "Sky illuminance": ["a", "g"],
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
        # <TBC> requires extra inputs from user
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
    }

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
    time_dict = {"Julian": ["*", "a"], "DateTime": ["*", "a", "*", "a"]}
    if time_fmt is not None:
        csv_open = [">", "temp.csv", "desc"] + time_dict[time_fmt] + ["&", "^", "e"]
    else:
        csv_open = [">", "temp.csv", "desc"] + ["&", "^", "e"]
    perf_met = ["g"]

    res_select = []
    zone_select = []
    for item in param_list:
        zone_input = item[0]
        metric_input = item[1]
        # ---------------------------------
        # Select all zones
        # ---------------------------------
        if zone_input == "all":
            res_select.append(["4", "*", "-"])
        # ---------------------------------
        # Multiple zone selections
        # ---------------------------------
        elif isinstance(zone_input, list) and len(zone_input) > 1:
            for j in zone_input:
                # Selection by id:
                if j[:3] == "id:":
                    selected_zone = j[3:]
                    chr_zone = [
                        chr(96 + ind + 1)
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
                # Assume direct letter selection of zones if len = 1
                elif len(j) == 1:
                    zone_select.append(j[0])
                else:
                    print("zone selection error for '{}', check input format".format(j))
            res_select.append(["4"] + zone_select + ["-"])
        # ---------------------------------
        # Single selection
        # ---------------------------------
        # From zone name
        elif zone_input[:3] == "id:":
            selected_zone = zone_input[3:]
            chr_zone = [
                chr(96 + ind + 1)
                for ind, x in enumerate(zone_names)
                if x == selected_zone
            ]
            # If exists select it, otherwise throw error
            if chr_zone:
                zone_select.append(chr_zone[0])
                res_select.append(["4"] + zone_select + ["-"])
            else:
                print("zone selection error, '{}' not found".format(selected_zone))
        # Assume single letter selection
        elif len(zone_input) == 1:
            zone_select.append(zone_input[0])
            res_select.append(["4"] + zone_select + ["-"])
        else:
            print(
                "zone selection error for '{}', check input format".format(zone_input)
            )
        # Select metric
        # If error in single selection, gets all zones (for now)
        res_select.append(res_dict[metric_input])

    # Flatten list
    res_select = list(itertools.chain.from_iterable(res_select))

    csv_close = ["!", ">"]
    res_close = ["-", "-", "-", "-"]

    cmd = res_open + csv_open + perf_met + res_select + csv_close + res_close
    cmd = "\n".join(cmd)
    # print(cmd)
    res = run(
        ["res", "-file", res_file, "-mode", "script"], input=cmd, encoding="ascii"
    )

    header_lines = 4
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
    os.remove("temp.csv")

    data_frame = pandas.read_csv(
        out_file, sep=",", header=0, index_col=0, parse_dates=True
    )

    return data_frame


def abovebelow(cfg_file, res_file, is_below=False, out_file=None, query_point=25):
    """Get hours above or below a value."""
    # Read cfg file for list of zones
    cfg = get.config(cfg_file)
    zones = cfg["zones"]

    # Get overheating stats from ESP-r to temporary file
    cmd = [
        "",
        "d",
        ">",
        "temp.csv",
        "",
        "^",
        "e",
        "d" if is_below else "c",
        "b",
        "a",
        "-",
        str(query_point),
        ">",
        "-",
        "-",
    ]
    cmd = "\n".join(cmd)
    res = run(
        ["res", "-file", res_file, "-mode", "script"],
        stdout=PIPE,
        stderr=PIPE,
        input=cmd,
        encoding="ascii",
        check=True,
    )

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
            elif line_count >= header + len(zones):
                break
            else:
                data.append(row)
                line_count += 1

    # remove temporary CSV file
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
        output.append(
            [
                row[0],
                float(row[idx_metric]),
                round(float(row[idx_metric]) / total_hours * 100, 1),
            ]
        )

    # Write back out to CSV
    if out_file is not None:
        headers = ["Zone", "Time (h)", "Frequency (%)"]
        with open(out_file, "w", newline="") as write_file:
            writer = csv.writer(write_file)
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
