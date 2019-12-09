"""Functions to convert between various file formats.
"""

import subprocess

from espy import get

# pylint: disable-msg=C0103


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

    geo = get.geometry(geo_file)
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


def epw_to_espr(epw_file, espr_file="newclim"):
    """Convert EPW file to ESP-r binary weather file.
    """

    cmd = ["*", espr_file, "k", "a", epw_file, "-"]
    cmd = "\n".join(cmd)
    subprocess.run(
        ["clm", "-mode", "script"],
        stdout=subprocess.PIPE,
        input=cmd,
        encoding="ascii",
        check=True,
    )


def weather_bin_to_ascii(bin_file, ascii_file="newclim.a"):
    """Convert ESP-r binary weather file to ascii file.
    """

    cmd = ["<", bin_file, "j", "a", ascii_file, "Y", "-"]
    cmd = "\n".join(cmd)
    subprocess.run(
        ["clm", "-mode", "script"],
        stdout=subprocess.PIPE,
        input=cmd,
        encoding="ascii",
        check=True,
    )