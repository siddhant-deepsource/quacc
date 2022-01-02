from htase.calculators.vasp import SmartVasp
from htase.schemas.vasp import summarize
from htase.util.atoms import make_slabs_from_bulk
from htase.util.calc import cache_calc
from ase.io.jsonio import encode, decode
from jobflow import job, Flow, Response
from shutil import copyfile
import os


@job
def run_slab_job(atoms_json, slab=True, static=False):
    atoms = decode(atoms_json)

    if static:
        updates = {
            "nsw": 0,
            "lwave": True,
            "lcharg": True,
            "laechg": True,
            "lvhar": True,
        }
    else:
        updates = {}

    if slab:
        atoms = SmartVasp(atoms, preset="SlabRelaxSet", **updates)
    else:
        atoms = SmartVasp(
            atoms,
            preset="SlabRelaxSet",
            ncore=4,
            kpar=16,
            auto_dipole=False,
            auto_kpts={"length_density": [50, 50, 50]},
            **updates,
        )

    atoms.get_potential_energy()
    atoms = cache_calc(atoms)

    return {
        "atoms": encode(atoms),
        "results": summarize.get_results(),
    }


@job
def run_dos(atoms_json):
    atoms = decode(atoms_json)
    atoms_results = atoms.info["results"]
    chgcar_path = os.path.join(
        atoms_results[f"calc{len(atoms_results)-1}"]["rundir"], "CHGCAR"
    )
    if os.path.exists(chgcar_path):
        copyfile(chgcar_path, "CHGCAR")
        icharg = 11
    else:
        icharg = 0
    atoms = SmartVasp(
        atoms,
        preset="SlabRelaxSet",
        nsw=0,
        icharg=icharg,
        ismear=-5,
        isym=2,
        nedos=3001,
    )
    atoms.get_potential_energy()
    atoms = cache_calc(atoms)
    return {
        "atoms": encode(atoms),
        "results": summarize.get_results(),
    }


@job
def bulk_to_slab_job(atoms_json):
    atoms = decode(atoms_json)

    slabs = make_slabs_from_bulk(atoms)
    jobs = []
    outputs = []
    for slab in slabs:
        relax_job = run_slab_job(encode(slab))
        jobs.append(relax_job)
        outputs.append(relax_job.output)

        static_job = run_slab_job(relax_job.output["atoms"], static=True)
        jobs.append(static_job)
        outputs.append(static_job.output)

        dos_job = run_dos(static_job.output["atoms"])
        jobs.append(dos_job)
        outputs.append(dos_job.output)

    return Response(replace=Flow(jobs, output=outputs))