"""Functions that directory edit ESP-r files."""
from espy.utils import sed

# pylint: disable-msg=C0103


def door_usage(geo_file, original, updated):
    """Directly edit door usage in geometry file.
    """

    options = ["CLOSED", "UNDERCUT", "OPEN", "BIDIRECTIONAL"]
    options_set = set(options)
    # Check that original and updated are valid options
    if original in options_set and updated in options_set:
        sed("DOOR," + original, "DOOR," + updated, geo_file)
    else:
        print("Invalid original or updated options provided. No changes being made.")


def window_usage(geo_file, original, updated):
    """Directly edit window usage in geometry file.
    """

    options = ["CLOSED", "CRACK", "OPEN", "SASH", "BIDIRECTIONAL"]
    options_set = set(options)
    # Check that original and updated are valid options
    if original in options_set and updated in options_set:
        sed("WINDOW," + original, "WINDOW," + updated, geo_file)
    else:
        print("Invalid original or updated options provided. No changes being made.")


def frame_usage(geo_file, original, updated):
    """Directly edit frame usage in geometry file.
    """

    options = ["CLOSED", "CRACK", "VENT"]
    options_set = set(options)
    # Check that original and updated are valid options
    if original in options_set and updated in options_set:
        sed("FRAME," + original, "FRAME," + updated, geo_file)
    else:
        print("Invalid original or updated options provided. No changes being made.")
