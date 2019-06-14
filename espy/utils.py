#!/usr/bin/env python3
"""Helper utilities"""
import re
from os import fdopen
from shutil import move
from tempfile import mkstemp


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
    print(source)
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
