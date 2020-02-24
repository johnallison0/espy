"""Functions to interact with prj."""
import itertools
from subprocess import PIPE, run

from espy import get


def edit_material_prop(cfg_file, change_list):
    """Edit material properties.
    This function will build the command list to edit material properties in
    the materials db via prj.
    """
    # NOTE: Edits are made in place with the existing database entires,
    # so backups/copies should be made before making changes.
    # TODO(j.allison): Do input and range checking

    # Open material database
    cmd_mat_open = ["b", "c", "a"]

    # change_list is provided as a list of lists of the changes i.e.
    # change_list =
    # [['class_chr', 'material_chr', 'material_prop', value]]
    map_prop_dict = {
        "conductivity": "c",
        "density": "d",
        "specific heat": "e",
        "emissivity out": "f",
        "emissivity in": "g",
        "absorptivity out": "h",
        "absorptivity in": "i",
        "vapour res": "j",
    }
    n_changes = len(change_list)
    cmd_mat = []
    for i in range(n_changes):
        cmd_mat_i = [
            change_list[i][0],
            change_list[i][1],
            map_prop_dict[change_list[i][2]],
            str(change_list[i][3]),
            "-",
            "Y",
            "-",
            "Y",
            "Y",
        ]
        cmd_mat.append(cmd_mat_i)
    # Flatten list
    cmd_mat = list(itertools.chain.from_iterable(cmd_mat))

    # Exit database maintenance, update mode name list and rebuild
    # existing zone construction files
    cmd_mat_close = ["-", "-", "Y", "Y", "-"]

    # Concatenate list of commands
    cmd = cmd_mat_open + cmd_mat + cmd_mat_close
    cmd = "\n".join(cmd)
    prj = run(
        ["prj", "-file", cfg_file, "-mode", "script"],
        stdout=PIPE,
        input=cmd,
        encoding="ascii",
    )
    return prj


def edit_layer_thickness(cfg_file, change_list):
    """Edit layer thickness of multi-layered construction.
    This function will build the command list to edit the layer thickness in
    the MLC db via prj.
    """
    # NOTE: Edits are made in place with the existing database entires,
    # so backups/copies should be made before making changes.
    # TODO(j.allison): Do input and range checking

    # Open construction database
    cmd_con_open = ["b", "e", "a"]

    # change_list is provided as a list of lists of the changes i.e.
    # change_list =
    # [['class_chr', 'construction_chr', layer_no, layer_thickness]]
    menu_offset = 11  # letter start offset
    n_changes = len(change_list)
    cmd_con = []
    for i in range(n_changes):
        layer_no_alpha = chr(96 + menu_offset + change_list[i][2])
        if change_list[i][3] > 300:
            cmd_con_i = [
                change_list[i][0],
                change_list[i][1],
                layer_no_alpha,
                "N",
                str(change_list[i][3]),
                "Y",
                "-",
                "-",
                "Y",
                "Y",
            ]
            print(
                "The input value for layer thickness in mm ({}) should be "
                "less than 300.".format(change_list[i][3])
            )
            print("Layer has been updated regardless.")
        else:
            cmd_con_i = [
                change_list[i][0],
                change_list[i][1],
                layer_no_alpha,
                "N",
                str(change_list[i][3]),
                "-",
                "-",
                "Y",
                "Y",
            ]
        cmd_con.append(cmd_con_i)
    # Flatten list
    cmd_con = list(itertools.chain.from_iterable(cmd_con))

    # Exit database maintenance, update mode name list and rebuild
    # existing zone construction files
    cmd_con_close = ["-", "-", "-", "Y", "Y", "-"]

    # Concatenate list of commands
    cmd = cmd_con_open + cmd_con + cmd_con_close
    cmd = "\n".join(cmd)
    prj = run(
        ["prj", "-file", cfg_file, "-mode", "script"],
        stdout=PIPE,
        input=cmd,
        encoding="ascii",
    )
    return prj


def gen_qa_report(cfg_file, filename):
    """Generate model QA report."""
    cmd = ["m", "u", "Y", ">", "../doc/" + filename, "!", "-", "-", "-"]
    cmd = "\n".join(cmd)
    prj = run(
        ["prj", "-file", cfg_file, "-mode", "script"],
        stdout=PIPE,
        input=cmd,
        encoding="ascii",
    )
    return prj


def rebuild_con_files(cfg_file):
    """Updates the zone construction files."""
    prj = run(
        ["prj", "-file", cfg_file, "-act", "update_zone_con", "-mode", "script"],
        stdout=PIPE,
    )
    return prj


def add_window(cfg_file, zone, surf, location, size, sill=None, reveal=None):
    """Adds window to a surface in a zone."""
    x_off, z_off = location
    width, height = size
    
    z_sel, geo_file = get.zone_selection(cfg_file, zone)
    geo = get.geometry(geo_file)
    n_surf = len(geo["edges"])

    # Insert opening
    geoatt_menu = ["m", "c", "a"]
    zone_select = [z_sel]
    insert = ["e", "+", "c"]
    surf_select = [get.surface_selection(geo_file, surf)]
    insert_type = ["a"]  # within surface
    dimensions = [f"{str(x_off)} {str(z_off)} {str(width)} {str(height)}"]

    # frame properties
    frame_name = ["frm_f"]  # TODO: Add option to set frame name
    frame_con = ["e", "e"]  # TODO: Add option to set construction (default to U = 2 PVC)
    frame_usage = ["b", "-", "a"]  # TODO: Add option to set usage (default FRAME FACADE: CLOSED)

    if sill is not None:
        temp_name = ["temp"]
        temp_con = ["+"]  # UNKNOWN
        temp_usage = ["i", "-"]  # Something else
        temp_extrude = ["+", "h", chr(96 + n_surf + 1), str(sill)]  # newest surface
        reveal_inv = ["<"] + [chr(96 + n_surf + i) for i in range(2, 7)] + ["-"]
        temp_rm = ["*", chr(96 + n_surf + 1), "-"]
    else:
        temp_name = frame_name
        temp_con = frame_con
        temp_usage = frame_usage
        temp_extrude = []
        reveal_inv = []
        temp_rm = []

    # Insert glazing as percentage of frame opening
    insert2 = ["+", "c"]
    frame_select = [chr(96 + n_surf + 1)]
    insert2_type = ["c", str(90)]  # insert as % of surface area

    # glazing properties
    glz_name = ["glz"]  # TODO: Add option to set glazing name
    glz_con = ["d", "a"]  # # TODO: Add option to set construction (default to dbl glz)
    glz_usage = ["e", "-", "a"]  # TODO: Add option to set usage (WINDOW: CLOSED)

    cmd = (
        geoatt_menu
        + zone_select
        + insert
        + surf_select
        + insert_type
        + dimensions
        + temp_name
        + temp_con
        + temp_usage
        + ["Y"]
        + temp_extrude
        + reveal_inv
        + temp_rm
        + insert2
        + frame_select
        + insert2_type
        + glz_name
        + glz_con
        + glz_usage
        + ["Y"]
        + ["-"] * 2
        + ["Y"]
        + ["-"] * 5
    )
    cmd = "\n".join(cmd)
    # print(cmd)

    prj1 = run(
        ["prj", "-mode", "script", "-file", cfg_file],
        stdout=PIPE,
        stderr=PIPE,
        input=cmd,
        encoding="ascii",
        check=True,
    )

    # external window reveals
    if reveal is not None:
        geo = get.geometry(geo_file)  # re-read geo file with window added
        frame_corners = geo["edges"][n_surf][:3] + geo["edges"][n_surf][-1:]
        ex_reveals = ["h", "a", "@", "c", chr(96 + n_surf + 1), "rev", str(reveal), "e", "e", "a", " ".join([str(i) for i in frame_corners]), ">"]

        cmd = (
            geoatt_menu
            + zone_select
            + ex_reveals
            + ["-"] * 5
        )
        cmd = "\n".join(cmd)
        # print(cmd)

        prj2 = run(
                ["prj", "-mode", "script", "-file", cfg_file],
                stdout=PIPE,
                stderr=PIPE,
                input=cmd,
                encoding="ascii",
                check=True,
            )
    else:
        prj2 = []
    return prj1, prj2

def add_zone(
    cfg_file, name, vertices, description=None, z_base=0, z_top=2.7, rot_angle=0
):
    """Adds new zone to model."""
    cfg = get.config(cfg_file)

    geoatt_menu = ["m", "c", "a"]
    if cfg["zones"] is not None:
        add_zone = ["*", "a"]
        cnn_file = []
    else:
        add_zone = []
        cnn_file = ["", ""]  # accept default
    # a) input dimensions, b) load existing (ESP-r), c) loading existing (cflow 3 zip), e) use pre-defined entity, f) cancel
    new_zone_options = ["a"]
    if len(name) > 12:
        name = name[0:12]
    if description is None:
        description = " "
    elif len(description) > 64:
        description = description[0:64]
    # a) rectangular plan, b) polygon plan, c) general 3D, e) bitmap
    zone_geo_type = ["b"]
    text_xyvertices = [f"{str(v[0])} {str(v[1])}" for v in vertices]
    prj_exit = ["-"] * 6

    # Verbose
    print(f"{name}: {description}")
    sup2 = "\u00B2"
    sup3 = "\u00B3"
    print(f"Floor area, A = {get.area(vertices):.3f} m{sup2}")
    print(f"Zone volume, V = {get.area(vertices)*z_top:.3f} m{sup3}")
    for i, v in enumerate(vertices):
        print(f"X&Y for v{i+1:3d} is   {v[0]:.4f}  {v[1]:.4f}")

    cmd = (
        geoatt_menu
        + add_zone
        + new_zone_options
        + [name]
        + [description]
        + zone_geo_type
        + [str(z_base)]
        + [str(z_top)]
        + [str(len(vertices))]
        + text_xyvertices
        + ["Y"]
        + [str(rot_angle)]
        + cnn_file
        + prj_exit
    )
    cmd = "\n".join(cmd)
    # print(cmd)

    prj = run(
        ["prj", "-mode", "script", "-file", cfg_file],
        stdout=PIPE,
        stderr=PIPE,
        input=cmd,
        encoding="ascii",
        check=True,
    )
    return prj
