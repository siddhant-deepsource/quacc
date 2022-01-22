from pymatgen.command_line.bader_caller import bader_analysis_from_path
from pymatgen.command_line.chargemol_caller import ChargemolAnalysis
import os


def run_bader(path=None):
    """
    Runs a Bader partial charge and spin moment analysis using the VASP
    output files in the given path. This function requires that `bader` or
    `bader.exe` is located in your PATH environment variable. See
    http://theory.cm.utexas.edu/henkelman/code/bader for the bader code.
    Note: If you want to use Bader on a code other than VASP, this function
    will need to be slightly modified.
    Args:
        path (str): The path where the VASP output files are located.
            Must include CHGCAR, AECCAR0, AECCAR2, and POTCAR files. These
            files can be gzip'd or not -- it doesn't matter.
            Default: None (current working directory).

    Returns:
        Dictionary containing the Bader analysis summary:
            {
                "min_dist": List[float],
                "atomic_volume": List[float],
                "vacuum_charge": float,
                "vacuum_volume": float,
                "bader_version": float,
                "partial_charges": List[float],
                "spin_moments": List[float],
            }

    """

    if path is None:
        path = os.getcwd()

    # Make sure files are present.
    for f in ["CHGCAR", "AECCAR0", "AECCAR2", "POTCAR"]:
        if not os.path.exists(os.path.join(path, f)) and not os.path.exists(
            os.path.join(path, f"{f}.gz")
        ):
            raise FileNotFoundError("Could not find {f} in {path}")

    # Run Bader analysis
    bader_stats = bader_analysis_from_path(path)

    # Store the partial charge, which is much more useful than the
    # raw charge and is more intuitive than the charge transferred.
    # An atom with a positive partial charge is cationic, whereas
    # an atom with a negative partial charge is anionic.
    bader_stats["partial_charges"] = [-c for c in bader_stats["charge_transfer"]]

    # Some cleanup of the returned dictionary
    if "magmom" in bader_stats:
        bader_stats["spin_moments"] = bader_stats["magmom"]
    else:
        bader_stats["spin_moments"] = [0.0] * len(bader_stats["partial_charge"])
    bader_stats.pop("charge", None)
    bader_stats.pop("charge_transfer", None)
    bader_stats.pop("reference_used", None)
    bader_stats.pop("magmom", None)

    return bader_stats


def run_chargemol(path=None, atomic_densities_path=None):
    """
    Runs a Chargemol (i.e. DDEC6 + CM5) analysis using the VASP output files
    in the given path. This function requires that the chargemol executable,
    given by the name `Chargemol_09_26_2017_linux_parallel`,
    `Chargemol_09_26_2017_linux_serial`, or `chargemol` is in the system PATH
    environment variable. See https://sourceforge.net/projects/ddec/files for
    the Chargemol code. Note: If you want to use Chargemol on a code other
    than VASP, this function will need to be slightly modified.

    Args:
        path (str): The path where the VASP output files are located.
            Must include CHGCAR, AECCAR0, AECCAR2, and POTCAR files. These
            files can be gzip'd or not -- it doesn't matter.
            Default: None (current working directory).
        atomic_densities_path (str): The path where the reference atomic densities
            are located for Chargemol. If None, we assume that this
            directory is defined in an environment variable named DDEC6_ATOMIC_DENSITIES_DIR.
            See the Chargemol documentation for more information.

    Returns:
        Dictionary containing the Chargemol analysis summary:
            {
                "ddec": {
                            "partial_charges": List[float],
                            "spin_moments": List[float],
                            "dipoles": List[float],
                            "bond_order_sums": List[float],
                            "bond_order_dict": Dict
                        },
                "cm5": {
                            "partial_charges": List[float],
                        }
            }
    """
    if path is None:
        path = os.getcwd()

    # Make sure files are present.
    for f in ["CHGCAR", "AECCAR0", "AECCAR2", "POTCAR"]:
        if not os.path.exists(os.path.join(path, f)) and not os.path.exists(
            os.path.join(path, f"{f}.gz")
        ):
            raise FileNotFoundError(f"Could not find {f} in {path}")

    # Run Chargemol analysis
    chargemol_stats = ChargemolAnalysis(
        path=path,
        atomic_densities_path=atomic_densities_path,
    )

    # Some cleanup of the returned dictionary
    if "spin_moments" not in chargemol_stats["ddec"]:
        chargemol_stats["ddec"]["spin_moments"] = [0.0] * len(
            chargemol_stats["ddec"]["partial_charge"]
        )
    chargemol_stats.pop("rsquared_moments", None)
    chargemol_stats.pop("rcubed_moments", None)
    chargemol_stats.pop("rfourth_moments", None)

    return chargemol_stats