"""Functions to interact with prj."""
import itertools
from subprocess import PIPE, run


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
        ["prj", "-file", cfg_file, "-mode", "script"], stdout=PIPE, input=cmd, encoding="ascii"
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
        ["prj", "-file", cfg_file, "-mode", "script"], stdout=PIPE, input=cmd, encoding="ascii"
    )
    return prj

def gen_qa_report(cfg_file, filename):
    """Generate model QA report."""
    cmd = ["m", "u", "Y", ">", "../doc/" + filename, "!", "-", "-", "-"]
    cmd = "\n".join(cmd)
    prj = run(
        ["prj", "-file", cfg_file, "-mode", "script"], stdout=PIPE, input=cmd, encoding="ascii"
    )
    return prj


def rebuild_con_files(cfg_file):
    """Updates the zone construction files."""
    prj = run(
        ["prj", "-file", cfg_file, "-act", "update_zone_con", "-mode", "script"], stdout=PIPE
    )
    return prj
