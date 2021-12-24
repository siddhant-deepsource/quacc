import os
from ase.io import read
from ase.build import bulk
from ase.calculators.vasp import Vasp
from htase.calculators.vasp import SmartVasp
from pathlib import Path
import numpy as np

FILE_DIR = Path(__file__).resolve().parent
DEFAULT_CALCS_DIR = os.path.join(FILE_DIR, "..", "..", "defaults", "user_calcs", "vasp")
TOL = 1e-5


def test_vanilla_smartvasp():
    atoms = bulk("Cu")
    atoms = SmartVasp(atoms, incar_copilot=False)
    assert atoms.calc.asdict() == Vasp().asdict()


def test_presets():
    atoms = bulk("Co") * (2, 2, 1)
    atoms[-1].symbol = "Fe"

    atoms_fullpath = SmartVasp(
        atoms, preset=os.path.join(DEFAULT_CALCS_DIR, "BulkRelaxSet")
    )
    atoms = SmartVasp(atoms, preset="BulkRelaxSet")
    assert atoms == atoms_fullpath
    assert atoms.calc.xc.lower() == "pbe"
    assert atoms.calc.string_params["algo"] == "fast"
    assert atoms.calc.exp_params["ediff"] == 1e-5
    assert atoms.calc.int_params["isif"] == 3

    atoms = SmartVasp(atoms, xc="rpbe", preset="SlabRelaxSet")
    assert atoms.calc.xc.lower() == "rpbe"
    assert atoms.calc.string_params["algo"] == "fast"
    assert atoms.calc.exp_params["ediff"] == 1e-5
    assert atoms.calc.int_params["isif"] == 2

    atoms = SmartVasp(atoms, xc="scan", preset="MPScanRelaxSet")
    assert atoms.calc.xc.lower() == "scan"
    assert atoms.calc.string_params["algo"] == "all"
    assert atoms.calc.exp_params["ediff"] == 1e-5
    assert atoms.calc.int_params["isif"] == 3


def test_lmaxmix():
    atoms = bulk("Cu")
    atoms = SmartVasp(atoms)
    assert atoms.calc.int_params["lmaxmix"] == 4

    atoms = bulk("Ce")
    atoms = SmartVasp(atoms)
    assert atoms.calc.int_params["lmaxmix"] == 6

    atoms = bulk("Cu") * (2, 2, 2)
    atoms[-1].symbol = "Ce"
    atoms = SmartVasp(atoms)
    assert atoms.calc.int_params["lmaxmix"] == 6


def test_ediff_per_atom():
    atoms = bulk("Cu") * (2, 2, 2)
    atoms = SmartVasp(atoms, ediff_per_atom=1e-4)
    assert atoms.calc.exp_params["ediff"] == 1e-4 * len(atoms)


def test_magmoms():
    atoms = bulk("Cu") * (2, 2, 1)
    atoms[-1].symbol = "Fe"
    atoms = SmartVasp(atoms, preset="BulkRelaxSet")
    assert atoms.get_initial_magnetic_moments().tolist() == [1.0] * (len(atoms) - 1) + [
        5.0
    ]

    atoms = bulk("Cu") * (2, 2, 1)
    atoms[-1].symbol = "Fe"
    atoms = SmartVasp(atoms, preset="BulkRelaxSet", mag_default=2.5)
    assert atoms.get_initial_magnetic_moments().tolist() == [2.5] * (len(atoms) - 1) + [
        5.0
    ]

    atoms = bulk("Eu") * (2, 2, 1)
    atoms[-1].symbol = "Fe"
    atoms = SmartVasp(atoms, preset="SlabRelaxSet")
    assert atoms.get_initial_magnetic_moments().tolist() == [10.0] * (
        len(atoms) - 1
    ) + [5.0]

    atoms = bulk("Cu") * (2, 2, 1)
    atoms[-1].symbol = "Fe"
    atoms = SmartVasp(atoms, preset="MPScanRelaxSet")
    assert atoms.get_initial_magnetic_moments().tolist() == [1.0] * (len(atoms) - 1) + [
        5.0
    ]

    atoms = bulk("Cu") * (2, 2, 1)
    atoms[-1].symbol = "Fe"
    atoms.set_initial_magnetic_moments([3.14] * (len(atoms) - 1) + [1.0])
    atoms = SmartVasp(atoms, preset="BulkRelaxSet")
    assert atoms.get_initial_magnetic_moments().tolist() == [3.14] * (
        len(atoms) - 1
    ) + [1.0]

    atoms = bulk("Co") * (2, 2, 1)
    atoms[-1].symbol = "Fe"
    atoms.set_initial_magnetic_moments([0.0] * len(atoms))
    atoms = SmartVasp(atoms, preset="BulkRelaxSet")
    assert np.all(atoms.get_initial_magnetic_moments() == 0.0)

    atoms = read(os.path.join(FILE_DIR, "OUTCAR_test.gz"))
    mags = atoms.get_magnetic_moments()
    atoms = SmartVasp(atoms, preset="BulkRelaxSet")
    assert np.array_equal(atoms.get_initial_magnetic_moments(), mags) is True

    atoms = read(os.path.join(FILE_DIR, "OUTCAR_test.gz"))
    mags = atoms.get_magnetic_moments()
    atoms = SmartVasp(atoms, preset="BulkRelaxSet", copy_magmoms=False)
    assert atoms.has("initial_magmoms") is False

    atoms = read(os.path.join(FILE_DIR, "OUTCAR_test.gz"))
    mags = atoms.get_magnetic_moments()
    atoms = SmartVasp(atoms, preset="BulkRelaxSet", mag_cutoff=2.0)
    assert atoms.has("initial_magmoms") is False


def test_unused_flags():
    atoms = bulk("Cu")
    atoms = SmartVasp(atoms, preset="BulkRelaxSet", potim=1.5, nsw=0)
    assert atoms.calc.int_params["nsw"] == 0
    assert atoms.calc.exp_params["ediffg"] is None
    assert atoms.calc.int_params["isif"] is None
    assert atoms.calc.float_params["potim"] is None

    atoms = SmartVasp(atoms, ldau=False, ldauprint=2)
    assert atoms.calc.int_params["ldauprint"] is None
    assert atoms.calc.bool_params["ldau"] is None


def test_lasph():
    atoms = bulk("Cu")

    atoms = SmartVasp(atoms, xc="rpbe")
    assert atoms.calc.bool_params["lasph"] is None

    atoms = SmartVasp(atoms, metagga="m06l")
    assert atoms.calc.bool_params["lasph"] is True

    atoms = SmartVasp(atoms, metagga="m06l", lasph=False)
    assert atoms.calc.bool_params["lasph"] is True

    atoms = SmartVasp(atoms, metagga="hse06")
    assert atoms.calc.bool_params["lasph"] is True

    atoms = SmartVasp(atoms, metagga="beef-vdw")
    assert atoms.calc.bool_params["lasph"] is True

    atoms = SmartVasp(atoms, ldau_luj={"Cu": {"L": 2, "U": 5, "J": 0.0}})
    assert atoms.calc.bool_params["lasph"] is True


def test_lmaxtau():
    atoms = bulk("Cu")
    atoms = SmartVasp(atoms, lasph=True)
    assert atoms.calc.int_params["lmaxtau"] is None

    atoms = bulk("Ce")
    atoms = SmartVasp(atoms, lasph=True)
    assert atoms.calc.int_params["lmaxtau"] == 8

    atoms = bulk("Cu") * (2, 2, 2)
    atoms[-1].symbol = "Ce"
    atoms = SmartVasp(atoms, lasph=True)
    assert atoms.calc.int_params["lmaxtau"] == 8


def test_algo():
    atoms = bulk("Cu")

    atoms = SmartVasp(atoms, xc="rpbe")
    assert atoms.calc.string_params["algo"] is None

    atoms = SmartVasp(atoms, metagga="m06l")
    assert atoms.calc.string_params["algo"] == "all"

    atoms = SmartVasp(atoms, metagga="m06l", algo="fast")
    assert atoms.calc.string_params["algo"] == "all"

    atoms = SmartVasp(atoms, metagga="hse06")
    assert atoms.calc.string_params["algo"] == "all"


def test_ismear():
    atoms = bulk("Cu")

    atoms = SmartVasp(atoms, nsw=10)
    assert atoms.calc.int_params["ismear"] is None

    atoms = SmartVasp(atoms, ismear=-5, nsw=10)
    assert atoms.calc.int_params["ismear"] == 1

    atoms = SmartVasp(atoms, ismear=-5, nsw=0)
    assert atoms.calc.int_params["ismear"] == 0

    atoms = SmartVasp(atoms, kpts=(10, 10, 10), ismear=-5, nsw=0)
    assert atoms.calc.int_params["ismear"] == -5

    atoms = SmartVasp(atoms, ismear=0, nsw=10)
    assert atoms.calc.int_params["ismear"] == 0

    atoms = SmartVasp(atoms, nedos=3001, nsw=0)
    assert atoms.calc.int_params["ismear"] == 0

    atoms = SmartVasp(atoms, ismear=-5, nedos=3001, nsw=0)
    assert atoms.calc.int_params["ismear"] == 0

    atoms = SmartVasp(atoms, kpts=(10, 10, 10), nedos=3001, nsw=0)
    assert atoms.calc.int_params["ismear"] == -5

    atoms = SmartVasp(atoms, auto_kpts={"line_density": 100}, ismear=1)
    assert atoms.calc.int_params["ismear"] == 0
    assert atoms.calc.float_params["sigma"] == 0.01

    atoms = SmartVasp(atoms, auto_kpts={"line_density": 100}, ismear=0, sigma=1e-3)
    assert atoms.calc.int_params["ismear"] == 0
    assert atoms.calc.float_params["sigma"] == 1e-3

    atoms = SmartVasp(atoms, auto_kpts={"line_density": 100}, ismear=-5)
    assert atoms.calc.int_params["ismear"] == 0

    atoms = SmartVasp(atoms, kspacing=1.0, ismear=-5)
    assert atoms.calc.int_params["ismear"] == 0
    assert atoms.calc.float_params["sigma"] == 0.05

    atoms = SmartVasp(atoms, nsw=0, kspacing=1.0, ismear=1, sigma=0.1)
    assert atoms.calc.int_params["ismear"] == 1
    assert atoms.calc.float_params["sigma"] == 0.1


def test_laechg():
    atoms = bulk("Cu")
    atoms = SmartVasp(atoms, nsw=10, laechg=True)
    assert atoms.calc.bool_params["laechg"] is None

    atoms = SmartVasp(atoms, laechg=True)
    assert atoms.calc.bool_params["laechg"] is True

    atoms = SmartVasp(atoms, nsw=0, laechg=True)
    assert atoms.calc.bool_params["laechg"] is True

    atoms = SmartVasp(atoms, nsw=0, laechg=False)
    assert atoms.calc.bool_params["laechg"] is False


def test_ldauprint():
    atoms = bulk("Cu")

    atoms = SmartVasp(atoms, ldau=True)
    assert atoms.calc.int_params["ldauprint"] == 1

    atoms = SmartVasp(atoms, ldau=True, ldauprint=0)
    assert atoms.calc.int_params["ldauprint"] == 1

    atoms = SmartVasp(atoms, ldau=False, ldauprint=1)
    assert atoms.calc.int_params["ldauprint"] is None

    atoms = SmartVasp(atoms, ldau_luj={"Cu": {"L": 2, "U": 5, "J": 0.0}})
    assert atoms.calc.int_params["ldauprint"] == 1


def test_lreal():
    atoms = bulk("Cu")
    atoms = SmartVasp(atoms, lreal=True, nsw=0)
    assert atoms.calc.special_params["lreal"] is False

    atoms = SmartVasp(atoms, lreal=True, nsw=10)
    assert atoms.calc.special_params["lreal"] is True

    atoms = SmartVasp(atoms, nsw=10)
    assert atoms.calc.special_params["lreal"] is None


def test_lorbit():
    atoms = bulk("Cu")

    atoms = SmartVasp(atoms, ispin=2)
    assert atoms.calc.int_params["lorbit"] == 11

    atoms = SmartVasp(atoms, ispin=1)
    assert atoms.calc.int_params["lorbit"] is None

    atoms.set_initial_magnetic_moments([1.0] * len(atoms))
    atoms = SmartVasp(atoms)
    assert atoms.calc.int_params["lorbit"] == 11


def test_setups():
    atoms = bulk("Cu")
    atoms = SmartVasp(atoms, preset="BulkRelaxSet")
    atoms.calc.parameters["setups"]["Cu"] == ""

    atoms = bulk("Cu")
    atoms = SmartVasp(atoms, preset="SlabRelaxSet")
    atoms.calc.parameters["setups"]["Ba"] == "_sv"
    atoms.calc.parameters["setups"]["Cu"] == ""

    atoms = bulk("Cu")
    atoms = SmartVasp(atoms, preset="MPScanRelaxSet")
    atoms.calc.parameters["setups"]["Cu"] == "_pv"

    atoms = bulk("Cu")
    atoms = SmartVasp(atoms, setups="minimal", preset="MPScanRelaxSet")
    assert (
        isinstance(atoms.calc.parameters["setups"], str)
        and atoms.calc.parameters["setups"] == "minimal"
    )


def test_kpoint_schemes():
    atoms = bulk("Cu")
    atoms = SmartVasp(atoms, kpts=[1, 1, 1], preset="BulkRelaxSet")
    assert atoms.calc.kpts == [1, 1, 1]

    atoms = bulk("Cu")
    atoms = SmartVasp(atoms, auto_kpts={"grid_density": 1000}, force_gamma=False)
    assert atoms.calc.kpts == [10, 10, 10]
    assert atoms.calc.input_params["gamma"] is False

    atoms = bulk("Cu")
    atoms = SmartVasp(atoms, auto_kpts={"grid_density": 1000})
    assert atoms.calc.kpts == [10, 10, 10]
    assert atoms.calc.input_params["gamma"] is True

    atoms = bulk("Cu")
    atoms = SmartVasp(
        atoms, auto_kpts={"grid_density": 1000}, force_gamma=False, gamma=True
    )
    assert atoms.calc.kpts == [10, 10, 10]
    assert atoms.calc.input_params["gamma"] is True

    atoms = bulk("Cu")
    atoms = SmartVasp(atoms, auto_kpts={"reciprocal_density": 100})
    assert atoms.calc.kpts == [12, 12, 12]

    atoms = bulk("Cu")
    atoms = SmartVasp(atoms, auto_kpts={"max_mixed_density": [100, 1000]})
    assert atoms.calc.kpts == [12, 12, 12]

    atoms = bulk("Cu")
    atoms = SmartVasp(atoms, auto_kpts={"length_density": [50, 50, 1]})
    assert atoms.calc.kpts == [20, 20, 1]

    atoms = bulk("Cu")
    atoms = SmartVasp(atoms, auto_kpts={"line_density": 100})
    assert (
        np.max(
            np.abs(
                atoms.calc.kpts[-1, :]
                - np.array([1.30537091e00, 1.11022302e-16, 1.30537091e00])
            )
        )
    ) < TOL