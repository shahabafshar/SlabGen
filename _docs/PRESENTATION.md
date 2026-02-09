# SlabGen: An Integrated Platform for Systematic Surface Generation, Visualization, and DFT Workflow Preparation

Shahab Afsharghoochani and Zeinab Hajali Fard
Iowa State University

14th Annual GPSS Research Conference | February 20, 2026

<!-- Use --- as slide breaks. Compatible with Marp, reveal.js, Slidev, etc. -->

---

## Why Surfaces?

Almost every interaction between a material and its environment happens at the surface.

- **Catalysis** — reaction rates depend on which crystal face is exposed
- **Corrosion** — certain surfaces degrade faster than others
- **Thin films and coatings** — growth behavior depends on surface termination
- **Crystal growth** — equilibrium shape is dictated by surface energies

Understanding surfaces computationally starts with a deceptively simple task: cutting a slab from a bulk crystal along a chosen crystallographic plane.

---

## The Problem

In practice, generating surface slabs is tedious and error-prone.

The typical workflow today looks like this:

1. Write a Python script using pymatgen's `SlabGenerator`
2. Manually inspect the output for correctness
3. Repeat for every Miller index and termination you care about
4. Separately write VASP input files by hand

**Common mistakes along the way:**

- Wrong surface termination (different atomic layer exposed than intended)
- Polar surfaces that produce unphysical dipoles
- Atom stretching and distortion at high-index orientations like (2,1,0) or (3,1,1)
- No easy way to see what you've generated without loading it into VESTA or another tool

> There is no single tool that connects structure sourcing, slab generation, visualization, screening, and DFT preparation into one workflow.

---

## SlabGen

SlabGen is an open-source desktop application that integrates the full surface science workflow in one place.

**Input:** Bulk crystal structure from the Materials Project database or a local file (VASP POSCAR, CIF)

**What it does:**

- Generates surface slabs for any Miller index (h,k,l)
- Interactive 3D visualization — rotate, zoom, inspect
- Screens all symmetrically distinct surfaces at once
- Prepares complete VASP DFT input file sets (POSCAR, INCAR, KPOINTS)

**Built with:** Python, PyQt5, pymatgen, matplotlib

**Available at:** github.com/shahabafshar/SlabGen (MIT license)

<!-- SLIDE NOTE: Show architecture diagram here — MP/File → Generate → Visualize → Screen → DFT -->

---

## The Two-Step Algorithm

Direct slab generation at high Miller indices can produce distorted structures where atoms are stretched or compressed unnaturally. SlabGen avoids this with a two-step approach:

**Step 1 — Orient and replicate**

Take the bulk crystal and rotate it so the desired (h,k,l) plane aligns with the z-axis. Then replicate along z to build up slab thickness.

```
SlabGenerator(structure, miller_index=(h,k,l), min_vac=0)
→ oriented slab
→ make_supercell([1, 1, z_reps])
```

**Step 2 — Add vacuum and terminations**

Apply a second SlabGenerator pass with (0,0,1) — now a trivial cut — to add vacuum spacing and enumerate all possible surface terminations.

```
SlabGenerator(oriented_slab, miller_index=(0,0,1), min_vac=vacuum)
→ final slab(s) with vacuum and correct terminations
```

This separation keeps the geometry clean even for high-index surfaces.

<!-- SLIDE NOTE: A simple before/after diagram works well here — show a distorted direct slab vs. the clean two-step result -->

---

## Live Demo

<!-- This slide is a placeholder for the live demonstration. Practice this sequence beforehand and have backup screenshots/video ready. -->

**Workflow to demonstrate:**

1. Search "Mo2C" in the Materials Project panel — select a structure — bulk crystal appears in the 3D viewer
2. Set Miller index to (0,0,1), Z Reps = 3, Vacuum = 15 A — click **Generate Slabs** — slab appears, rotate it around
3. Click **Screen All Surfaces** — the screening dialog runs with a progress bar — results table fills in with all symmetrically distinct surfaces
4. Select an interesting surface from the table — click **Load in Main** — it appears in the 3D viewer
5. Click **Prepare DFT Inputs** — adjust ENCUT, ISMEAR, dipole correction — preview the INCAR — generate all files to a directory

**Estimated time: 3 minutes**

If the demo fails, switch to the pre-recorded video or static screenshots.

---

## The Interface

<!-- INSERT: Full-window screenshot of SlabGen showing Mo2C in the 3D viewer -->

**Layout:**

| Section | What it does |
|---------|-------------|
| Top panel | Search Materials Project by formula, or upload a local POSCAR/CIF file |
| Slab options | Set Miller indices (h,k,l), slab thickness (Z reps), vacuum, centering |
| Advanced | Toggle all terminations, surface comparison, screening |
| Middle | Generated slabs list (left) + interactive 3D viewer (right) |
| Bottom | Export slab as VASP/CIF, or generate full DFT input sets |

The 3D viewer uses Jmol colors and element-scaled atom sizes. Atoms render in front of the unit cell wireframe for clarity.

---

## Surface Screening

SlabGen can screen all symmetrically distinct surfaces for a material in a single pass.

**How it works:**

- Uses pymatgen's `get_symmetrically_distinct_miller_indices()` to find all unique orientations up to a maximum Miller index
- For each orientation, generates all possible terminations using the two-step algorithm
- Reports: Miller index, shift (termination), atom count, surface area, symmetry, composition
- Runs in a background thread — the GUI stays responsive

**Output:**

- Sortable results table (green = symmetric slab, yellow = asymmetric)
- One-click CSV export for further analysis
- Any surface can be loaded directly back into the main window

<!-- INSERT: Screenshot of the screening dialog with results table populated -->

---

## DFT Input Generation

For any generated slab, SlabGen produces a complete set of VASP input files ready for HPC submission.

**Generated files:**

| File | Contents |
|------|----------|
| POSCAR | Slab structure |
| INCAR | Relaxation parameters (ISIF=2 for slabs, automatic dipole correction) |
| KPOINTS | Gamma-centered mesh with k_z = 1 along the vacuum direction |
| POTCAR.spec | Element list for pseudopotential selection |
| job.sh | SLURM submission script template |

**Key settings are configurable through the GUI:**

ENCUT, ISMEAR/SIGMA, EDIFFG, ISIF (slab vs. bulk), dipole correction toggle. An INCAR preview updates live as you adjust parameters.

<!-- INSERT: Screenshot of the DFT dialog showing the INCAR preview -->

---

## Case Study: Mo2C

Molybdenum carbide (Mo2C) is a material of interest for heterogeneous catalysis and hard coating applications. Its surface properties are not fully characterized.

We used SlabGen to systematically study Mo2C surfaces:

1. **Loaded** Mo2C from the Materials Project database
2. **Screened** all symmetrically distinct surfaces up to max Miller index 2
3. **Identified** all unique terminations, flagged symmetric vs. asymmetric slabs
4. **Generated** VASP input sets for selected surfaces
5. **Submitted** slab and bulk reference calculations to ISU HPC

<!-- INSERT: Table of screening results — Miller index, # terminations, symmetric/asymmetric -->

---

## Screening Results: Mo2C

<!-- INSERT: Formatted screening results table from CSV export -->

**Key observations:**

- Number of unique Miller indices found: ___
- Total number of distinct terminations: ___
- Symmetric slabs: ___
- Asymmetric slabs (requiring dipole correction): ___

Some Miller indices produce multiple terminations with very different surface compositions — the (h,k,l) alone doesn't fully define a surface. The termination (shift value) matters.

---

## Surface Energies

Surface energy tells us how much energy it costs to create a unit area of surface:

$$\gamma = \frac{E_{\text{slab}} - n \cdot E_{\text{bulk}}}{2A}$$

| Surface | Atoms | Area (A^2) | Energy (J/m^2) |
|---------|-------|-----------|-----------------|
| (0,0,1) | ___ | ___ | ___ |
| (1,0,0) | ___ | ___ | ___ |
| (1,1,0) | ___ | ___ | ___ |
| (1,1,1) | ___ | ___ | ___ |

<!-- Fill in from VASP results. Typical carbide range: 1.0–4.0 J/m^2. Multiply eV/A^2 by 16.02 to get J/m^2. -->

Lower surface energy = more thermodynamically stable surface = more likely to appear on the equilibrium crystal shape.

<!-- INSERT: Bar chart comparing surface energies across Miller indices -->

---

## Wulff Construction

<!-- This slide is a stretch goal — include only if DFT results are available in time -->

The Wulff construction predicts the equilibrium crystal shape from surface energies. Surfaces with lower energy occupy larger fractions of the crystal facets.

<!-- INSERT: Wulff shape figure generated from pymatgen's WulffShape -->

**Area fractions:**

| Facet | Fraction |
|-------|----------|
| (0,0,1) | ___ |
| (1,0,0) | ___ |
| (1,1,0) | ___ |
| (1,1,1) | ___ |

This shape represents the minimum-energy morphology of a Mo2C nanoparticle — a prediction that can be compared against TEM observations.

---

## What SlabGen Enables

**Before SlabGen:**
Write custom scripts for each material. Manually track Miller indices, terminations, file paths. Debug stretching artifacts. Generate DFT inputs separately. Takes hours to days per material.

**With SlabGen:**
Load a structure, screen all surfaces in minutes, visualize them interactively, generate DFT-ready input sets with a few clicks. The entire pipeline from crystal structure to HPC submission fits in one session.

This matters because systematic surface studies — where you want to compare many surfaces of the same material — were previously impractical for most research groups due to the scripting overhead.

---

## Future Directions

- **Surface energy database** — collect and compare surface energies across materials
- **Adsorption site identification** — find high-symmetry sites on generated surfaces for catalysis studies
- **Multi-code support** — extend DFT output beyond VASP to Quantum ESPRESSO, CP2K, and others
- **Convergence testing** — automated slab thickness and vacuum convergence workflows
- **Web interface** — make SlabGen accessible without local installation

---

## Acknowledgments

- Iowa State University
- Materials Project API
- pymatgen development team

**SlabGen is open source and freely available:**

github.com/shahabafshar/SlabGen

<!-- INSERT: QR code linking to GitHub repository -->

Questions?
