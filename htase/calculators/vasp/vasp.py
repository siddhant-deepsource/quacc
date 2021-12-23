from htase.utilities.calc import load_yaml_calc
from ase.calculators.calculator import CalculatorSetupError
from ase.calculators.vasp import Vasp
from pymatgen.io.vasp.inputs import Kpoints
from pymatgen.io.ase import AseAtomsAdaptor
from pymatgen.symmetry.bandstructure import HighSymmKpath
import numpy as np
import os
import warnings
from pathlib import Path

DEFAULT_CALCS_DIR = os.path.join(
    Path(__file__).resolve().parent, "..", "..", "defaults", "user_calcs", "vasp"
)


def SmartVasp(
    atoms,
    preset=None,
    incar_copilot=True,
    force_gamma=True,
    copy_magmoms=True,
    mag_cutoff=0.05,
    verbose=True,
    **kwargs,
):
    """
    This is a wrapper around the VASP calculator that adjusts INCAR parameters on-the-fly.
    Also supports several automatic k-point generation schemes from Pymatgen.

    Parameters
    ----------
    atoms : ase.Atoms
        The Atoms object to be used for the calculation.
    preset : str
        The path to a .yaml file containing a list of INCAR parameters to use as a "preset"
        for the calculator. If no filepath is present, it will look in htase/defaults/user_calcs, such
        that preset="bulk_base" is supported. It will append .yaml at the end if not present.
    incar_copilot : bool
        If True, the INCAR parameters will be adjusted if they go against the VASP manual.
        Defaults to True.
    force_gamma : bool
        If True, the KPOINTS will always be set to gamma-centered.
        Defaults to True.
    copy_magmoms : bool
        If True, any pre-existing atoms.get_magnetic_moments() will be set in atoms.set_initial_magnetic_moments().
        Defaults to True.
    mag_cutoff : float
        If copy_magmoms is True, only copy atoms.get_magnetic_moments() if there is at least one atom with an 
        absolute magnetic moment above mag_cutoff.
        Defaults to 0.05.
    verbose : bool
        If True, warnings will be raised when INCAR parameters are changed.
        Defaults to True.
    **kwargs :
        Additional arguments to be passed to the VASP calculator, e.g. xc='PBE', encut=520. Takes all valid 
        ASE calculator arguments, in addition to the ones listed below:
            auto_kpts
            elemental_magmoms
    
    Returns
    -------
    atoms : ase.Atoms
        The ASE Atoms object with attached VASP calculator.
    """

    # Grab the pymatgen structure object in case we need it later
    struct = AseAtomsAdaptor().get_structure(atoms)

    # Get user-defined preset parameters for the calculator
    if preset:
        _, ext = os.path.splitext(preset)
        if not ext:
            preset += ".yaml"
        if os.path.exists(preset):
            calc_preset = load_yaml_calc(preset)["inputs"]
        elif os.path.exists(os.path.join(DEFAULT_CALCS_DIR, preset)):
            calc_preset = load_yaml_calc(os.path.join(DEFAULT_CALCS_DIR, preset))[
                "inputs"
            ]
        else:
            raise ValueError(f"Cannot find {preset}")
    else:
        calc_preset = {}

    # Collect all the calculator parameters and prioritize the kwargs
    # in the case of duplicates.
    user_calc_params = {**calc_preset, **kwargs}
    none_keys = [k for k, v in user_calc_params.items() if v is None]
    for none_key in none_keys:
        user_calc_params.pop(none_key)

    # If the user explicitly requests gamma = False, let's honor that
    # over force_gamma.
    if user_calc_params.get("gamma", None):
        user_gamma = user_calc_params["gamma"]
        if force_gamma is True:
            warnings.warn(
                "force_gamma is True but gamma is requested to be False. We will not force gamma-centered k-points."
            )
        force_gamma = False
    else:
        user_gamma = None

    # If the preset has auto_kpts but the user explicitly requests kpts, then
    # we should honor that.
    if (
        kwargs.get("kpts", None) is not None
        and calc_preset.get("auto_kpts", None) is not None
    ):
        user_calc_params.pop("auto_kpts")

    # If the preset has ediff_per_atom but the user explicitly requests ediff, then
    # we should honor that.
    if (
        kwargs.get("ediff", None) is not None
        and calc_preset.get("ediff_per_atom", None) is not None
    ):
        user_calc_params.pop("ediff_per_atom")

    # Handle special arguments in the user calc parameters that
    # ASE does not natively support
    if user_calc_params.get("elemental_magmoms", None) is not None:
        elemental_mags_dict = user_calc_params["elemental_magmoms"]
        del user_calc_params["elemental_magmoms"]
    else:
        elemental_mags_dict = {}
    if user_calc_params.get("auto_kpts", None) is not None:
        auto_kpts = user_calc_params["auto_kpts"]
        del user_calc_params["auto_kpts"]
    else:
        auto_kpts = None
    if user_calc_params.get("ediff_per_atom", None) is not None:
        ediff_per_atom = user_calc_params["ediff_per_atom"]
        del user_calc_params["ediff_per_atom"]
    else:
        ediff_per_atom = None

    # Shortcuts for pymatgen k-point generation schemes.
    # Options include: line_density (for band structures),
    # reciprocal_density (by volume), grid_density (by number of atoms),
    # max_mixed_density (max of reciprocal_density volume or atoms), and length_density (good for slabs).
    # These are formatted as {"line_density": float}, {"reciprocal_density": float},
    # {"grid_density": float}, {"vol_kkpa_density": [float, float]}, and
    # {"length_density": [float, float, float]}.
    if auto_kpts:

        if auto_kpts.get("line_density", None) is not None:
            kpath = HighSymmKpath(struct, path_type="latimer_munro")
            kpts, _ = kpath.get_kpoints(
                line_density=auto_kpts["line_density"], coords_are_cartesian=True
            )
            user_calc_params["kpts"] = kpts
            user_calc_params["reciprocal"] = True

        else:
            if auto_kpts.get("max_mixed_density", None) is not None:
                if len(auto_kpts["max_mixed_density"]) != 2:
                    raise ValueError("Must specify two values for max_mixed_density.")

                pmg_kpts1 = Kpoints.automatic_density_by_vol(
                    struct, auto_kpts["max_mixed_density"][0], force_gamma
                )
                pmg_kpts2 = Kpoints.automatic_density(
                    struct, auto_kpts["max_mixed_density"][1], force_gamma
                )
                if np.product(pmg_kpts1.kpts[0]) >= np.product(pmg_kpts2.kpts[0]):
                    pmg_kpts = pmg_kpts1
                else:
                    pmg_kpts = pmg_kpts2
            elif auto_kpts.get("reciprocal_density", None) is not None:
                pmg_kpts = Kpoints.automatic_density_by_vol(
                    struct, auto_kpts["reciprocal_density"], force_gamma
                )
            elif auto_kpts.get("grid_density", None) is not None:
                pmg_kpts = Kpoints.automatic_density(
                    struct, auto_kpts["grid_density"], force_gamma
                )
            elif auto_kpts.get("length_density", None) is not None:
                if len(auto_kpts["length_density"]) != 3:
                    raise ValueError("Must specify three values for length_density.")
                pmg_kpts = Kpoints.automatic_density_by_lengths(
                    struct, auto_kpts["length_density"], force_gamma
                )
            else:
                raise ValueError(f"Unsupported k-point generation scheme: {auto_kpts}.")

            kpts = pmg_kpts.kpts[0]
            if pmg_kpts.style.name.lower() == "gamma":
                gamma = True
            else:
                gamma = False

            user_calc_params["kpts"] = kpts
            if user_gamma is None:
                user_calc_params["gamma"] = gamma

    # Handle ediff_per_atom if present
    if ediff_per_atom:
        user_calc_params["ediff"] = ediff_per_atom * len(atoms)

    # Handle the magnetic moments
    # Check if there are converged magmoms
    try:
        mags = atoms.get_magnetic_moments()
    except RuntimeError or CalculatorSetupError:
        mags = None

    # Check if the user has set any initial magmoms
    has_initial_mags = np.any([hasattr(atom, "magmom") for atom in atoms])

    # Copy converged magmoms to input magmoms, if copy_magmoms is True
    # and if any are above mag_cutoff
    if mags and copy_magmoms and np.any(np.abs(mags > mag_cutoff)):
        atoms.set_initial_magnetic_moments(mags)

    # If there are no initial magmoms set, we may need to add some
    # from the preset yaml.
    if not has_initial_mags:

        # If the preset dictionary has default magmoms, set
        # those by element. If the element isn't in the magmoms dict
        # then set it to 1.0 (VASP default).
        if elemental_mags_dict:
            initial_mags = np.array(
                [elemental_mags_dict.get(atom.symbol, 1.0) for atom in atoms]
            )
            atoms.set_initial_magnetic_moments(initial_mags)

    # Turn off EDIFFG/IBRION/ISIF/POTIM if NSW = 0
    opt_flags = ["ediffg", "ibrion", "isif", "potim"]
    if user_calc_params.get("nsw", 0) == 0:
        for opt_flag in opt_flags:
            user_calc_params.pop(opt_flag, None)

    # Turn off +U flags if +U is not even used
    ldau_flags = [
        "ldau",
        "ldauu",
        "ldauj",
        "ldaul",
        "ldautype",
        "ldauprint",
        "ldau_luj",
    ]
    if not user_calc_params.get("ldau", False) and not user_calc_params.get(
        "ldau_luj", None
    ):
        for ldau_flag in ldau_flags:
            user_calc_params.pop(ldau_flag, None)

    # Instantiate the calculator!
    calc = Vasp(**user_calc_params)

    # Handle INCAR swaps as needed
    if incar_copilot:

        if (
            not calc.int_params["lmaxmix"]
            or calc.int_params["lmaxmix"] < 6
            and any(atoms.get_atomic_numbers() > 56)
        ):
            if verbose:
                warnings.warn(
                    "Copilot: Setting LMAXMIX = 6 because you have an f-element."
                )
            calc.set(lmaxmix=6)
        elif (
            not calc.int_params["lmaxmix"]
            or calc.int_params["lmaxmix"] < 4
            and any(atoms.get_atomic_numbers() > 20)
        ):
            if verbose:
                warnings.warn(
                    "Copilot: Setting LMAXMIX = 4 because you have a d-element"
                )
            calc.set(lmaxmix=4)

        if (
            calc.bool_params["luse_vdw"]
            or calc.bool_params["lhfcalc"]
            or calc.bool_params["ldau"]
            or calc.dict_params["ldau_luj"]
            or calc.string_params["metagga"]
        ) and not calc.bool_params["lasph"]:
            if verbose:
                warnings.warn(
                    "Copilot: Setting LASPH = True because you have a +U, vdW, meta-GGA, or hybrid calculation."
                )
            calc.set(lasph=True)

        if (
            calc.bool_params["lasph"]
            and (calc.int_params["lmaxtau"] and calc.int_params["lmaxtau"] < 8)
            and np.max(atoms.get_atomic_numbers()) > 56
        ):
            if verbose:
                warnings.warn(
                    "Copilot: Setting LMAXTAU = 8 because you have LASPH = True and an f-element."
                )
            calc.set(lmaxtau=8)

        if (calc.bool_params["lhfcalc"] or calc.string_params["metagga"]) and (
            calc.string_params["algo"] and calc.string_params["algo"].lower() != "all"
        ):
            if verbose:
                warnings.warn(
                    "Copilot: Setting ALGO = All because you have a meta-GGA or hybrid calculation."
                )
            calc.set(algo="All")

        if (
            calc.int_params["nedos"]
            and calc.int_params["ismear"] != -5
            and calc.int_params["nsw"] in (None, 0)
            and np.product(calc.kpts >= 4)
        ):
            if verbose:
                warnings.warn(
                    "Copilot: Setting ISMEAR = -5 because you have a static DOS calculation and enough k-points."
                )
            calc.set(ismear=-5)

        if calc.int_params["ismear"] == -5 and np.product(calc.kpts) < 4:
            if verbose:
                warnings.warn(
                    "Copilot: Setting ISMEAR = 0 because you don't have enough k-points for ISMEAR = -5."
                )
            calc.set(ismear=0)

        if (
            calc.float_params["kspacing"]
            and calc.float_params["kspacing"] > 0.5
            and calc.int_params["ismear"] == -5
        ):
            if verbose:
                warnings.warn(
                    "Copilot: KSPACING might be too large for ISMEAR = -5. Custodian should save you if needed, but you can also change ISMEAR to 0."
                )
            pass  # let Custodian deal with it

        if (
            calc.int_params["nsw"]
            and calc.int_params["nsw"] > 0
            and calc.bool_params["laechg"]
        ):
            if verbose:
                warnings.warn(
                    "Copilot: Setting LAECHG = False because you have NSW > 0. LAECHG is not compatible with NSW > 0."
                )
            calc.set(laechg=False)

        if calc.bool_params["ldauprint"] in (None, 0) and calc.bool_params["ldau"]:
            if verbose:
                warnings.warn("Copilot: Setting LDAUPRINT = 1 because LDAU = True.")
            calc.set(laechg=False)

        if calc.special_params["lreal"] and calc.int_params["nsw"] in (None, 0, 1):
            if verbose:
                warnings.warn(
                    "Copilot: Setting LREAL = False because you are running a static calculation. LREAL != False can be bad for energies."
                )
            calc.set(lreal=False)

        if not calc.int_params["lorbit"] and (
            calc.int_params["ispin"] == 2
            or np.any(atoms.get_initial_magnetic_moments() != 0)
        ):
            if verbose:
                warnings.warn(
                    "Copilot: Setting LORBIT = 11 because you have a spin-polarized calculation."
                )
            calc.set(lorbit=11)

        if calc.int_params["luse_vdw"] and "ASE_VASP_VDW" not in os.environ:
            raise EnvironmentError(
                "ASE_VASP_VDW was not set, yet you requested a vdW functional."
            )

    calc.discard_results_on_any_change = True
    atoms.calc = calc

    return atoms
