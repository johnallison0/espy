"""Write out various files."""


def construction(fout, constr_name, constr_data, air_gap_data, mat_names):
    """Write out construction data in markdown format.

    Args:
        constr_name: str
            Construction name.

        constr_data: list
            List of construction data layers and thermophysical properties.

        air_gap_data: list
            List of air gap locations and properties.

        mat_names: list
            List of str of length N with name of each material layer.

    Returns:
        out_file: str
            Filename of open out file.
    """
    column_headers = [
        "Layer",
        "Material",
        "Thickness / mm",
        "Thermal conductivity / W\u00b7m^-1^\u00b7K^-1^",
        "Density / kg\u00b7m^-3^",
        "Specific heat / J\u00b7kg^-1^\u00b7K^-1^",
        "Emissivity",
        "Absorptivity",
    ]
    header_str = ["-" * len(x) for x in column_headers]
    out_file = f"../doc/{constr_name}.md"
    mat_names = ["mat"] * len(constr_data)
    if air_gap_data is not None:
        idx_air_gaps = air_gap_data[0::2]
    else:
        idx_air_gaps = []
    # with open(out_file, "w", encoding="utf8") as fout:
    for i, (layer, mat) in enumerate(zip(constr_data, mat_names)):
        if i == 0:
            fout.write("|" + "|".join(column_headers) + "|")
            fout.write("\n|" + "|".join(header_str) + "|")
            name = "1 (Ext)"
        elif i == len(constr_data) - 1:
            name = f"{len(constr_data)} (Int)"
        else:
            name = i + 1
        if i in (0, len(constr_data) - 1):
            dat_line = f"\n|{name}|{mat}|{1000*layer[3]:.0f}|{layer[0]:.3g}|{layer[1]:.0f}|{layer[2]:.0f}|{layer[8]:.2f}|{layer[9]:.2f}|"
        elif i + 1 in idx_air_gaps:
            dat_line = f"\n|{name}|air gap|{1000*layer[3]:.0f}|---|---|---|---|---|"
        else:
            dat_line = f"\n|{name}|{mat}|{1000*layer[3]:.0f}|{layer[0]:.3g}|{layer[1]:.0f}|{layer[2]:.0f}|---|---|"
        fout.write(dat_line)
    fout.write(f"\n\n  : Thermophysical properties of construction.")
    return out_file


def img_to_md(fout, img_file, caption):
    """Generate markdown format image text."""
    return fout.write(f"![{caption}]({img_file})")
