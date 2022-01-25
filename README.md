![example workflow](https://github.com/arosen93/quacc/actions/workflows/workflow.yaml/badge.svg)
[![codecov](https://codecov.io/gh/arosen93/quacc/branch/main/graph/badge.svg?token=BCKGTD89H0)](https://codecov.io/gh/arosen93/quacc)
[![CodeFactor](https://www.codefactor.io/repository/github/arosen93/quacc/badge)](https://www.codefactor.io/repository/github/arosen93/quacc)

# QuAcc (🚧 Under Construction 🚧)
The Quantum Accelerator (QuAcc) supercharges your code to support high-throughput, database-driven density functional theory (DFT). QuAcc is built with the following goals in mind:
- Rapid workflow development, no matter your favorite code.
    - QuAcc is built on top of [ASE](https://wiki.fysik.dtu.dk/ase/index.html) for calculation setup and execution, providing native support for dozens of DFT packages through a common interface. Through the use of [cclib](https://github.com/cclib/cclib) and [pymatgen](https://pymatgen.org/), there's a single interface for output parsing too.
- A database-oriented approach that is as easy to use for 1 calculation as it is for 10,000.
    - QuAcc makes it easy to integrate ASE with [Jobflow](https://materialsproject.github.io/jobflow/) for the simple construction of complex workflows and ability to store results in database format. By extension, this also makes it possible to easily use ASE with [Fireworks](https://github.com/materialsproject/fireworks) for job management.
- On-the-fly error handling and "smart" calculators.
    - For VASP, QuAcc comes pre-packaged with a `SmartVasp` calculator that can run calculations via [Custodian](https://github.com/materialsproject/custodian) for on-the-fly error handling, an optional "co-pilot" mode to ensure your input arguments don't go against what is in the [VASP manual](https://www.vasp.at/wiki/index.php/Main_page), and more.
- Seamless collaboration.
    - QuAcc makes it possible to read in pre-defined ASE calculator configurations with settings defined in YAML format.

In practice, the goal here is to enable the development of [Atomate2](https://github.com/materialsproject/atomate2)-like workflows centered around ASE with a focus on rapid workflow construction and prototyping.
<p align="center">
<img src="https://imgs.xkcd.com/comics/standards_2x.png" alt="xkcd Comic" width="528" height="300">
<p align="center">
Credit: xkcd
</p>

## Minimal Examples
### SmartVasp Calculator
In direct analogy to the conventional way of running ASE, QuAcc has a calculator called `SmartVasp()` that takes any of the [input arguments](https://wiki.fysik.dtu.dk/ase/ase/calculators/vasp.html#ase.calculators.vasp.Vasp) in a typical ASE `Vasp()` calculator but supports several additional keyword arguments to supercharge your workflow. It can also adjust your settings on-the-fly if they go against the VASP manual. The main differences for the seasoned ASE user are that the first argument must be an ASE `Atoms` object, and it returns an `Atoms` object with an enhanced `Vasp()` calculator already attached.

The example below runs a relaxation of bulk Cu using the RPBE functional with the remaining settings taken from a pre-defined set ("preset") of calculator input arguments.

```python
from quacc.calculators.vasp import SmartVasp
from ase.build import bulk

atoms = bulk("Cu") # example Atoms object
atoms = SmartVasp(atoms, xc='rpbe', preset="BulkRelaxSet") # set calculator
atoms.get_potential_energy() # run VASP w/ Custodian
```

### Jobflow Integration
The above example can be converted to a format suitable for constructing a Jobflow flow simply by defining it in a function with a `@job` wrapper immediately preceeding it. One nuance of Jobflow is that the inputs and outputs must be JSON serializable (so that it can be easily stored in a database), but otherwise it works the same.

```python
from quacc.calculators.vasp import SmartVasp
from quacc.schemas.vasp import summarize_run
from ase.io.jsonio import decode
from jobflow import job

#-----Jobflow Function-----
@job
def run_relax(atoms_json):

    # Run VASP
    atoms = SmartVasp(decode(atoms_json), xc='rpbe', preset="BulkRelaxSet")
    atoms.get_potential_energy()
    
    # Return serialized results
    summary = summarize_run(atoms)
    return summary
```
```python
from ase.build import bulk
from ase.io.jsonio import encode
from jobflow import Flow
from jobflow.managers.local import run_locally

#-----Make and Run a Flow-----
# Constrct an Atoms object
atoms = bulk("Cu")

# Define the flow
job1 = run_relax(encode(atoms))
flow = Flow([job1])

# Run the flow
run_locally(flow, create_folders=True)
```
### Fireworks Integration
For additional details on how to convert a Jobflow job or flow to a Fireworks firework or workflow, refer to the [Jobflow documentation](https://materialsproject.github.io/jobflow/jobflow.managers.html#module-jobflow.managers.fireworks). 

## Installation
1. Run the following command in a convenient place to install QuAcc:
```bash
git clone https://github.com/arosen93/quacc.git
cd quacc && pip install -r requirements.txt && pip install -e .
```

2. Follow the instructions in ASE's [documentation](https://wiki.fysik.dtu.dk/ase/ase/calculators/calculators.html#supported-calculators) for how to set up the ASE calculator(s) you plan to use.

3. Define the following environment variables (e.g. in your `~/.bashrc`) if you wish to use Jobflow and/or Fireworks, in addition to any that you have set in Step 2. Example `.yaml` files are provided [here](https://github.com/arosen93/quacc/tree/main/quacc/setup).

```bash
# Jobflow requirements
# (details: https://materialsproject.github.io/jobflow/jobflow.settings.html)
export JOBFLOW_CONFIG_FILE="/path/to/config/jobflow_config/jobflow.yaml"

# FireWorks requirements
# (details: https://materialsproject.github.io/fireworks)
export FW_CONFIG_FILE='/path/to/config/fw_config/FW_config.yaml'

```
## License
QuAcc is released under a [modified BSD license](https://github.com/arosen93/quacc/blob/main/LICENSE.md).
