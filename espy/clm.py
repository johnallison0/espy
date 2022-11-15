"""Functions to interact with clm."""
from subprocess import PIPE, run


def get_avg_degree_days(weather_file, temp_base=15.5):
    """Returns the daily average degree days"""
    cmd = ["", ">", "temp.csv", "^", "e", "c", "5", "a", str(temp_base), "-", ">", "-"]
    cmd = "\n".join(cmd)
    clm = run(
        ["clm", "-mode", "script", "-file", weather_file],
        input=cmd,
        stdout=PIPE,
        stderr=PIPE,
        encoding="ascii",
    )
    with open("temp.csv", "r") as f_in:
        lines = f_in.read().splitlines()
        last_line = lines[-2].split(",")[1]
    return float(last_line)
    

def epw_to_espr(epw_file, espr_file="newclim"):
    """Convert EPW file to ESP-r binary weather file.
    """

    cmd = ["*", espr_file, "k", "a", epw_file, "-"]
    cmd = "\n".join(cmd)
    run(
        ["clm", "-mode", "script"],
        stdout=PIPE,
        input=cmd,
        encoding="ascii",
        check=True,
    )

    
def weather_bin_to_ascii(bin_file, ascii_file="newclim.a"):
    """Convert ESP-r binary weather file to ascii file.
    """

    cmd = ["<", bin_file, "j", "a", ascii_file, "Y", "-"]
    cmd = "\n".join(cmd)
    run(
        ["clm", "-mode", "script"],
        stdout=PIPE,
        input=cmd,
        encoding="ascii",
        check=True,
    )
