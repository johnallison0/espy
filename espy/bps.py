"""Functions to interact with res."""
from subprocess import PIPE, run


def run_sim(
        cfg_file, res_file,
        sim_start_d, sim_start_m, sim_end_d, sim_end_m, start_up_d, tsph, integrate
    ):
    """Run basic simulation."""
    # Only designed to work for models without additional networks eg. massflow
    cmd = [
        "",
        "c",
        res_file,
        "{} {}".format(sim_start_d, sim_start_m),
        "{} {}".format(sim_end_d, sim_end_m),
        "{}".format(start_up_d),
        "{}".format(tsph),
        integrate,
        "s",
        "Y",
        "description",
        "Y",
        "Y",
        "-",
        "-",
    ]
    cmd = "\n".join(cmd)
    bps = run(
        ["bps", "-file", cfg_file, "-mode", "script"], stdout=PIPE, input=cmd, encoding="ascii"
    )
    return bps
