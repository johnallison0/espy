#!/usr/bin/env python3
"""Low level utilities"""
import re
from os import fdopen
from shutil import move
from tempfile import mkstemp
import numpy as np
import datetime as dt
from calendar import monthrange


def header(str_in, lvl=0):
    header_format = {
        0: "=" * 80 + f"\n {str_in}\n" + "=" * 80,
        1: "-" * 40 + f"\n {str_in}\n" + "-" * 40,
        2: "*" * 30 + f"\n {str_in}\n" + "*" * 30
    }
    return header_format.get(lvl, str_in)


def split_to_float(string):
    """Transform CSV string into list of floats."""
    return [float(x) for x in string.split(",")]


def space_data_to_list(item, convert="int"):
    """Transform space separated data into specified type list"""
    if convert == "int":
        y = [int(item[0])] + [int(x) for x in item[1].split(" ") if x is not ""]
    elif convert == "float":
        y = [float(item[0])] + [float(x) for x in item[1].split(" ") if x is not ""]
    else:
        "Unrecognised convert type."
    return y


def sed(pattern, replace, source, dest=None, count=0):
    """Reads a source file and writes the destination file.

    In each line, replaces pattern with replace.

    Args:
        pattern (str): pattern to match (can be re.pattern)
        replace (str): replacement str
        source  (str): input filename
        count (int): number of occurrences to replace
        dest (str):   destination filename, if not given, source will be over written.
    """
    fin = open(source, "r")
    num_replaced = count

    if dest:
        fout = open(dest, "w")
    else:
        file_handle, name = mkstemp()
        fout = fdopen(file_handle, "w")

    for line in fin:
        out = re.sub(pattern, replace, line)
        fout.write(out)

        if out != line:
            num_replaced += 1
        if count and num_replaced > count:
            break
    try:
        fout.writelines(fin.readlines())
    except Exception as the_except:
        raise the_except

    fin.close()
    fout.close()

    if not dest:
        move(name, source)

        
def area(poly):
    """area of polygon poly
    Source: https://stackoverflow.com/a/12643315
    Source 2: http://geomalgorithms.com/a01-_area.html#3D%20Polygons
    """

    if len(poly) < 3:  # not a plane - no area
        return 0

    total = [0, 0, 0]
    for i, _ in enumerate(poly):
        vi1 = poly[i]
        if i is len(poly) - 1:
            vi2 = poly[0]
        else:
            vi2 = poly[i + 1]
        prod = np.cross(vi1, vi2)
        total[0] += prod[0]
        total[1] += prod[1]
        total[2] += prod[2]
    result = np.linalg.norm(total)
    return round(result / 2, 3)

    
def dtparse_espr(d):
    """Parser for esp-r datetime format.

    This is useful for old versions of ESP-r (<13.3.15) because days
    did not match time steps intuitively.

    Example
        res.time_series('model.cfg','results.res',[['all','Zone db T']],out_file='results.csv')
        df = pandas.read_csv(
            'results.csv',
            index_col=0,
            parse_dates=True,
            date_parser = dtparse_espr)
    """
    lout=[]
    for a in d:
        la=a.split(' ')
        ld=la[0].split('-')
        lt=la[1].split(':')
        if lt[0]=='00' and lt[1]=='00':
            x = int(ld[2])+1
            if x > monthrange(int(ld[0]),int(ld[1]))[1]:
                x = int(ld[1])+1
                if x > 12:
                    lt = ['23','59','59']
                else:
                    ld[1] = str(x)
                    ld[2] = '1'
            else:
                ld[2] = str(x)
        lout.append(dt.datetime(int(ld[0]),int(ld[1]),int(ld[2]),hour=int(lt[0]),minute=int(lt[1]),second=int(lt[2])))
    return lout
