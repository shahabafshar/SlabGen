# SlabGen User Guide

## Getting Started

### Prerequisites
- Python 3.8+
- Install dependencies: `pip install -r requirements.txt`
- (Optional) Materials Project API key in `mp_api_key.txt`

### Launch
```bash
python main.py
```

---

## 1. Loading a Structure

You have two options for providing a bulk crystal structure:

### Option A: Search Materials Project
1. Enter a chemical formula in the **Formula** field (e.g., `Mo2C`, `TiO2`, `Cu`)
2. Click **Search**
3. A list of matching structures appears with material ID, formula, and space group
4. Click any result to **preview it in the 3D viewer**
5. The selected structure becomes the input for slab generation

**Requires**: API key in `mp_api_key.txt`. Get one from [materialsproject.org/api](https://materialsproject.org/api).

### Option B: Upload Local File
1. Click **Upload** in the right panel
2. Select a structure file from your computer
3. Supported formats: **VASP** (.vasp, POSCAR, CONTCAR), **CIF** (.cif)
4. The structure loads and previews in the 3D viewer

---

## 2. Generating Slabs

### Basic Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| **h, k, l** | Miller indices defining the surface plane | 0, 0, 1 |
| **Z Reps** | Number of unit cell repetitions along the surface normal (controls slab thickness) | 1 |
| **Vacuum** | Vacuum thickness in Angstroms added above/below the slab | 10.0 |
| **Vac Placement** | `top-only` places vacuum above; `centered` places slab in the middle of the vacuum | top-only |
| **Orthogonal c-axis** | Force the c-axis to be perpendicular to the surface | unchecked |

### How to Generate
1. Set your desired Miller indices and parameters
2. Click **Generate Slabs**
3. The generated slab(s) appear in the **Generated Slabs** list
4. The first slab is automatically selected and shown in the 3D viewer
5. Click different slabs to compare them visually

### Advanced Options

| Option | Description |
|--------|-------------|
| **All Terminations** | Generate all unique surface cuts (different atomic layers exposed at the surface) |
| **Do Comparison** | Compare top and bottom surfaces using RMSD to check symmetry |
| **Separate top/bot files** | Export the top and bottom surface layers as separate files (enabled when comparison is active) |
| **Depth** | How deep (in Angstroms) to extract the surface layers for comparison |

---

## 3. 3D Structure Viewer

The embedded viewer shows the currently selected structure with:
- Atoms colored by element (Jmol color scheme)
- Atom sizes proportional to atomic radius
- Unit cell bounding box (dashed lines)
- Interactive rotation, zoom, and pan via the matplotlib toolbar

The viewer updates automatically when you:
- Select a structure from Materials Project search results
- Upload a local file
- Select a slab from the generated list

---

## 4. Surface Screening

Screen **all symmetrically distinct surfaces** for a material at once.

### How to Use
1. Load a structure (search or upload)
2. Click **Screen All Surfaces**
3. In the dialog, set:
   - **Max Miller Index**: Maximum value for h, k, l (e.g., 2 generates all surfaces up to (2,2,2))
   - **Z Reps, Vacuum, Placement, Ortho**: Same as main window parameters
4. Click **Run Screening**
5. A progress bar tracks the screening process (runs in a background thread)

### Results Table
The results table shows for each surface termination:
- Miller index (h,k,l)
- Shift value (defines the termination)
- Number of atoms
- Surface area (Angstrom squared)
- Symmetric (Yes/No) — green = symmetric, yellow = asymmetric
- Chemical formula

The table is **sortable** by clicking any column header.

### Actions
- **Export to CSV**: Save the complete screening results as a spreadsheet
- **Load Selected in Main Window**: Send a specific surface back to the main window for visualization, export, or DFT preparation

---

## 5. DFT Input Generation

Generate ready-to-run VASP input files for the selected slab.

### How to Use
1. Select a slab from the generated list
2. Click **Prepare DFT Inputs**
3. Configure calculation settings (see table below)
4. Review the **INCAR Preview** — updates live as you change settings
5. Click **Generate DFT Inputs** and choose an output directory

### Settings

| Setting | Description | Default |
|---------|-------------|---------|
| **ENCUT** | Plane-wave energy cutoff (eV) | 400 |
| **K-point density** | k_product value; higher = denser k-mesh | 50 |
| **ISIF** | 2 = relax ions only (slab); 3 = relax ions + cell (bulk reference) | 2 |
| **ISMEAR** | Smearing method: 0 = Gaussian, 1 = MP, -5 = Tetrahedron | 0 |
| **SIGMA** | Smearing width (eV) | 0.05 |
| **EDIFFG** | Force convergence criterion (eV/Angstrom, negative = force-based) | -0.02 |
| **Auto dipole** | Apply dipole correction along c-axis (important for asymmetric slabs) | on |

### Generated Files
| File | Description |
|------|-------------|
| `POSCAR` | Slab structure in VASP format |
| `INCAR` | Calculation parameters |
| `KPOINTS` | K-point mesh (k_z = 1 for slabs) |
| `POTCAR.spec` | Element list (user must provide actual POTCAR from their VASP installation) |
| `job.sh` | SLURM submission script template |

---

## 6. Exporting Slabs

### Export as VASP or CIF
1. Select a slab from the list
2. Click **Export Selected Slab**
3. Choose format:
   - **VASP files (.vasp)** — standard POSCAR format for DFT codes
   - **CIF files (.cif)** — standard crystallographic format for databases and visualization tools

The suggested filename encodes all slab parameters:
```
POSCAR_{material}_{h}-{k}-{l}_z{reps}_vac{vacuum}_{placement}{ortho}_shift{shift}.vasp
```

---

## Typical Workflow

```
Load structure (MP or file)
    ↓
Screen All Surfaces (find interesting surfaces)
    ↓
Load selected surface into main window
    ↓
Visualize in 3D, adjust parameters if needed
    ↓
Export Slab (VASP or CIF)
    ↓
Prepare DFT Inputs (INCAR, KPOINTS, POSCAR)
    ↓
Submit to HPC cluster
    ↓
Calculate surface energies: γ = (E_slab - n·E_bulk) / (2·A)
```
