from typing import Any, Dict
from ase.io.jsonio import decode
from quacc.calculators.vasp import SmartVasp
from quacc.schemas.vasp import summarize_run
from jobflow import job, Maker
from dataclasses import dataclass


@dataclass
class RelaxMaker(Maker):
    """
    Class to relax a structure.

    Parameters
    ----------
    name:
        Name of the job.
    preset:
        Preset to use.
    ncore:
        VASP NCORE parameter.
    kpar:
        VASP KPAR parameter.
    """

    name: str = "Relax"
    preset: None | str = None
    ncore: int = 1
    kpar: int = 1

    @job
    def make(
        self, atoms_json: str, volume_relax: bool = True, **kwargs
    ) -> Dict[str, Any]:
        """
        Make the run.

        Parameters
        ----------
        atoms_json:
            Encoded .Atoms object
        volume_relax:
            True if a volume relaxation (ISIF = 3) should be performed.
            False if only the positions (ISIF = 2) should be updated.

        Returns
        -------
        Dict
            Summary of the run.
        """
        atoms = decode(atoms_json)
        if volume_relax:
            isif = 3
        else:
            isif = 2
        flags = {
            "ediff": 1e-5,
            "ediffg": -0.02,
            "isif": isif,
            "ibrion": 2,
            "ismear": 0,
            "isym": 0,
            "kpar": self.kpar,
            "lcharg": False,
            "lwave": False,
            "ncore": self.ncore,
            "nsw": 200,
            "sigma": 0.05,
        }
        for k, v in kwargs.items():
            flags[k] = v

        atoms = SmartVasp(atoms, preset=self.preset, **kwargs)
        atoms.get_potential_energy()
        summary = summarize_run(atoms)

        return summary


@dataclass
class StaticMaker(Maker):
    """
    Class to carry out a single-point calculation.

    Parameters
    ----------
    name:
        Name of the job.
    preset:
        Preset to use.
    ncore:
        VASP NCORE parameter.
    kpar:
        VASP KPAR parameter.
    """

    name: str = "Static"
    preset: None | str = None
    npar: int = 1
    kpar: int = 1

    @job
    def make(self, atoms_json: str, **kwargs) -> Dict[str, Any]:
        """
        Make the run.

        Parameters
        ----------
        atoms_json:
            Encoded .Atoms object

        Returns
        -------
        Dict
            Summary of the run.
        """
        atoms = decode(atoms_json)
        flags = {
            "ediff": 1e-6,
            "ismear": -5,
            "isym": 2,
            "kpar": self.kpar,
            "laechg": True,
            "lcharg": True,
            "lwave": True,
            "ncore": self.ncore,
            "nedos": 5001,
            "nsw": 0,
            "sigma": 0.05,
        }
        for k, v in kwargs.items():
            flags[k] = v

        atoms = SmartVasp(atoms, preset=self.preset, **kwargs)
        atoms.get_potential_energy()
        summary = summarize_run(atoms)

        return summary