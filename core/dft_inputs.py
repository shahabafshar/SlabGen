import os
from pymatgen.io.vasp.inputs import Poscar, Incar, Kpoints


# Default slab relaxation INCAR settings (based on MVLSlabSet)
DEFAULT_SLAB_INCAR = {
    "ALGO": "Fast",
    "EDIFF": 1e-5,
    "EDIFFG": -0.02,
    "ENCUT": 400,
    "IBRION": 2,
    "ISIF": 2,        # Relax ions only (fixed cell for slabs)
    "ISMEAR": 0,
    "SIGMA": 0.05,
    "ISYM": 0,
    "LREAL": "Auto",
    "NELMIN": 6,
    "NSW": 200,
    "PREC": "Accurate",
    "LWAVE": False,
    "LCHARG": False,
    "LVTOT": True,
}

# INCAR overrides for bulk reference calculation
BULK_OVERRIDES = {
    "ISIF": 3,        # Relax ions + cell
    "LVTOT": False,
}

# Default SLURM job script template
SLURM_TEMPLATE = """#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=36
#SBATCH --time=24:00:00
#SBATCH --partition=default

module load vasp
mpirun vasp_std
"""


class DFTInputGenerator:
    """Generate VASP input files for slab DFT calculations."""

    def __init__(self, slab):
        self.slab = slab

    def _build_incar_dict(self, config):
        """Build INCAR parameter dict from config. Single source of truth."""
        incar_dict = dict(DEFAULT_SLAB_INCAR)

        if config.get("is_bulk", False):
            incar_dict.update(BULK_OVERRIDES)

        # Apply user overrides
        if config.get("encut") is not None:
            incar_dict["ENCUT"] = config["encut"]
        if config.get("isif") is not None:
            incar_dict["ISIF"] = config["isif"]
        if config.get("ismear") is not None:
            incar_dict["ISMEAR"] = config["ismear"]
        if config.get("sigma") is not None:
            incar_dict["SIGMA"] = config["sigma"]
        if config.get("ediffg") is not None:
            incar_dict["EDIFFG"] = config["ediffg"]

        # Dipole correction for slabs
        if config.get("auto_dipole", True) and not config.get("is_bulk", False):
            frac_coords = self.slab.frac_coords
            center = frac_coords.mean(axis=0)
            incar_dict["LDIPOL"] = True
            incar_dict["IDIPOL"] = 3
            incar_dict["DIPOL"] = f"{center[0]:.4f} {center[1]:.4f} {center[2]:.4f}"

        if config.get("extra_incar"):
            incar_dict.update(config["extra_incar"])

        return incar_dict

    def generate(self, output_dir, config=None):
        """
        Write VASP input files to output_dir.

        config dict options:
            encut: int (default 400)
            k_product: int (default 50, for kpoint density)
            isif: int (2=relax ions, 3=relax ions+cell)
            ismear: int (default 0)
            sigma: float (default 0.05)
            ediffg: float (default -0.02)
            auto_dipole: bool (default True)
            is_bulk: bool (default False)
            extra_incar: dict (additional INCAR overrides)

        Returns dict of file paths written.
        """
        if config is None:
            config = {}

        os.makedirs(output_dir, exist_ok=True)

        # Build INCAR
        incar = Incar(self._build_incar_dict(config))

        # Build KPOINTS
        k_product = config.get("k_product", 50)
        kpoints = self._generate_kpoints(k_product, is_bulk=config.get("is_bulk", False))

        # Write files
        paths = {}

        poscar_path = os.path.join(output_dir, "POSCAR")
        Poscar(self.slab).write_file(poscar_path)
        paths["POSCAR"] = poscar_path

        incar_path = os.path.join(output_dir, "INCAR")
        incar.write_file(incar_path)
        paths["INCAR"] = incar_path

        kpoints_path = os.path.join(output_dir, "KPOINTS")
        kpoints.write_file(kpoints_path)
        paths["KPOINTS"] = kpoints_path

        # Write POTCAR.spec (element list, not actual pseudopotentials)
        spec_path = os.path.join(output_dir, "POTCAR.spec")
        elements = [str(el) for el in self.slab.composition.elements]
        with open(spec_path, "w") as f:
            f.write("\n".join(elements) + "\n")
        paths["POTCAR.spec"] = spec_path

        # Write SLURM job script
        job_name = config.get("job_name", "slab_relax")
        job_path = os.path.join(output_dir, "job.sh")
        with open(job_path, "w") as f:
            f.write(SLURM_TEMPLATE.format(job_name=job_name))
        paths["job.sh"] = job_path

        return paths

    def _generate_kpoints(self, k_product, is_bulk=False):
        """Generate KPOINTS based on lattice dimensions."""
        lengths = self.slab.lattice.abc
        kpts = []
        for i, length in enumerate(lengths):
            if i == 2 and not is_bulk:
                # c-direction is vacuum for slabs — always 1
                kpts.append(1)
            else:
                k = max(1, round(k_product / length))
                kpts.append(k)
        return Kpoints.gamma_automatic(kpts=tuple(kpts))

    def get_kpoints_string(self, config=None):
        """Return KPOINTS content as string for preview."""
        if config is None:
            config = {}
        k_product = config.get("k_product", 50)
        kpoints = self._generate_kpoints(k_product, is_bulk=config.get("is_bulk", False))
        return str(kpoints)

    def get_incar_preview(self, config=None):
        """Return INCAR content as string for preview."""
        if config is None:
            config = {}
        return str(Incar(self._build_incar_dict(config)))
