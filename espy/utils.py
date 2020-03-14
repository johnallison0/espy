#!/usr/bin/env python3
"""Helper utilities"""
import re
from os import fdopen
from shutil import move
from tempfile import mkstemp


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
