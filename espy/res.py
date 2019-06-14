"""Module to automate retrieval of data from res."""
import csv
import os
import itertools
from subprocess import PIPE, run
from espy import get


def time_series(cfg_file, res_file, out_file, param_list, time_fmt):
    """Extract results from results database to CSV.

    TODO(j.allison): if more than 42 this will break.

    param_list can be in the following format:
    param_list = [['all', 'Zone db T']]
    param_list = [['id:reception', 'Zone db T']]
    param_list = [[['id:roof_space', 'id:reception'], 'Zone db T']]
    param_list = [[['a', 'b'], 'Zone db T'], [['id:reception', 'b'], 'Wind direction']]
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
    _, _, _, _, _, _, zones = get.config(cfg_file)

    # Loop through each zone file and get zone name
    zone_names = []
    for ind, _ in enumerate(zones):
        file_path = zones[ind][1]["geo"]
        zone_names.append(get.geometry(file_path)["name"])

    res_open = ["", "c"]
    time_dict = {"Julian": ["*", "a"], "DateTime": ["*", "a", "*", "a"]}
    csv_open = [">", out_file, "desc"] + time_dict[time_fmt] + ["&", "^", "e"]
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
                        chr(96 + ind + 1) for ind, x in enumerate(zone_names) if x == selected_zone
                    ]
                    # If exists select it, otherwise throw error
                    if chr_zone:
                        zone_select.append(chr_zone[0])
                    else:
                        print("zone selection error, '{}' not found".format(selected_zone))
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
            chr_zone = [chr(96 + ind + 1) for ind, x in enumerate(zone_names) if x == selected_zone]
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
            print("zone selection error for '{}', check input format".format(zone_input))
        # Select metric
        # If error in single selection, gets all zones (for now)
        res_select.append(res_dict[metric_input])

    # Flatten list
    res_select = list(itertools.chain.from_iterable(res_select))

    csv_close = ["!", ">"]
    res_close = ["-", "-", "-"]

    cmd = res_open + csv_open + perf_met + res_select + csv_close + res_close
    cmd = "\n".join(cmd)
    res = run(
        ["res", "-file", res_file, "-mode", "script"], stdout=PIPE, input=cmd, encoding="ascii"
    )

    # Trim comment from header of file
    with open(out_file, "r") as infile, open("my" + out_file, "w", newline="") as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        line_count = 1
        for row in reader:
            if line_count == 4:
                newrow = ["Time"] + row[1:]
            else:
                newrow = row
            writer.writerow(newrow)
            line_count += 1

    return res


def overheating_stats(cfg_file, res_file, out_file=None, query_point=25):
    """Get overheating statistics."""
    # Read cfg file for list of zones
    _, _, _, _, _, _, zones = get.config(cfg_file)

    # Get overheating stats from ESP-r to temporary file
    cmd = [
        "",
        "d",
        ">",
        "temp.csv",
        "",
        "^",
        "e",
        "c",
        "b",
        "a",
        "-",
        str(query_point),
        ">",
        "-",
        "-",
    ]
    cmd = "\n".join(cmd)
    run(["res", "-file", res_file, "-mode", "script"], stdout=PIPE, input=cmd, encoding="ascii")

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
    except:
        print("Error while deleting file ", "temp.csv")

    # Calculate total number of hours
    total_hours = float(data[0][6]) + float(data[0][7])

    # Calculate percentage of time above limit
    overheating_frequency = []
    for zone in data:
        overheating_frequency.append([zone[0], round(float(zone[6]) / total_hours * 100, 1)])

    # Write back out to CSV that can be parsed by HighCharts
    if out_file is not None:
        headers = ["Zone", "Overheating frequency"]
        with open(out_file, "w", newline="") as write_file:
            writer = csv.writer(write_file)
            writer.writerow(headers)
            for zone in overheating_frequency:
                writer.writerow(zone)
    
    return overheating_frequency


def energy_balance(cfg_file, res_file, out_file=None):
    """Get zone energy balance."""
    # Read cfg file for list of zones
    _, _, _, _, _, _, zones = get.config(cfg_file)

    # Get zone energy balance from ESP-r to temporary file
    cmd = ["", "d", ">", "temp.csv", "", "^", "e", "h", "b", "b", ">", "-", "-"]
    cmd = "\n".join(cmd)
    run(["res", "-file", res_file, "-mode", "script"], stdout=PIPE, input=cmd, encoding="ascii")

    # Read CSV from ESP-r
    data = []
    for i in range(len(zones)):
        with open("temp.csv", "r") as file:
            reader = csv.reader(file, delimiter=",")
            data.append(
                [row for idx, row in enumerate(reader) if idx in range(19 * i + 6, 19 * i + 21)]
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

    return [headers[1:], total_gains[1:], total_losses[1:]]
