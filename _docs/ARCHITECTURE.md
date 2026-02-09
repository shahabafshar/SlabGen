# SlabGen Architecture Reference

## Module Structure

```
SlabGen/
├── main.py                    # Entry point — creates QApplication, launches MainWindow
├── core/                      # Business logic (no GUI dependencies)
│   ├── slab_generator.py      # Slab generation algorithm and structure utilities
│   ├── screening.py           # Batch surface screening engine
│   ├── dft_inputs.py          # VASP input file generation
│   └── visualization.py       # Matplotlib 3D structure plotting
├── ui/                        # PyQt5 GUI components
│   ├── main_window.py         # MainWindow (primary application window)
│   ├── viewer_widget.py       # StructureViewer (embeddable 3D canvas)
│   ├── screening_dialog.py    # ScreeningDialog + ScreeningWorker (QThread)
│   └── dft_dialog.py          # DFTInputDialog (VASP input configuration)
├── sample/                    # Sample structure files for testing
├── _docs/                     # Documentation
├── mp_api_key.txt             # Materials Project API key (not committed)
└── requirements.txt           # Python dependencies
```

---

## Core Modules

### core/slab_generator.py

The central algorithm module. All functions are pure (no GUI, no side effects).

**`oriented_slab_replication(structure, h, k, l, z_reps, min_vac, center_slab, all_terminations, force_ortho)`**
- Two-stage slab generation:
  1. Orient bulk so (h,k,l) aligns with z-axis using `SlabGenerator(miller_index=(h,k,l), min_vac=0)`
  2. Replicate along z with `make_supercell([1,1,z_reps])`
  3. Add vacuum via `SlabGenerator(miller_index=(0,0,1), min_vac=min_vac)`
  4. Optionally orthogonalize c-axis
- Returns: `list[Slab]`

**`extract_surface_regions(slab, compare_depth)`**
- Extracts top and bottom surface layers by z-coordinate range
- Rotates bottom 180 degrees for comparison
- Returns: `(top_struct, bottom_rotated)` — either can be None

**`compare_structures(top_struct, bottom_struct)`**
- Uses pymatgen `StructureMatcher` to check if top and bottom surfaces match
- Returns: `(is_match: bool, rmsd: float | None)`

### core/screening.py

**`SurfaceScreener(structure, max_index, z_reps, vacuum, center_slab, force_ortho)`**
- `.screen(progress_callback=None)` — generates all symmetrically distinct surfaces
- Uses `get_symmetrically_distinct_miller_indices()` from pymatgen
- For each Miller index, calls `oriented_slab_replication()` with `all_terminations=True`
- Collects: miller index, shift, atom count, surface area, is_symmetric, formula
- Returns: `list[dict]` (each dict also contains the `slab` object)

### core/dft_inputs.py

**`DFTInputGenerator(slab)`**
- `.generate(output_dir, config)` — writes POSCAR, INCAR, KPOINTS, POTCAR.spec, job.sh
- `.get_incar_preview(config)` — returns INCAR as string for live preview
- INCAR defaults based on MVLSlabSet: ISIF=2, ISMEAR=0, auto dipole correction
- KPOINTS: k_z = 1 for slabs (vacuum direction), k_product-based density for a,b
- Config dict keys: `encut`, `k_product`, `isif`, `ismear`, `sigma`, `ediffg`, `auto_dipole`, `is_bulk`, `extra_incar`

### core/visualization.py

**`plot_structure_3d(ax, structure, show_box=True, show_labels=True)`**
- Plots atoms on matplotlib Axes3D grouped by element
- Jmol color scheme (50+ elements defined in `JMOL_COLORS` dict)
- Atom sizes scaled by `Element.atomic_radius` from pymatgen
- Unit cell parallelepiped drawn as 12 dashed edges
- `computed_zorder = False` with manual zorder to keep atoms in front of box lines

---

## UI Modules

### ui/main_window.py — MainWindow

The primary application window. Contains all panels and coordinates between components.

**State:**
- `self.structure_docs` — list of MP API search result documents
- `self.selected_doc_index` — index of selected MP structure
- `self.local_structure` — Structure loaded from file (takes priority over MP)
- `self.generated_slabs` — list of Slab objects from last generation

**Key methods:**
- `_get_chosen_structure()` — returns the active bulk structure (local or MP)
- `generate_slabs()` — calls `oriented_slab_replication()`, populates list and viewer
- `_open_screening_dialog()` — opens ScreeningDialog with current structure
- `_open_dft_dialog()` — opens DFTInputDialog with selected slab
- `export_selected_slab()` — save as VASP or CIF

**Signal connections:**
- `struct_list_widget.itemClicked` → `on_doc_selected` (preview MP structure)
- `slabs_list_widget.currentRowChanged` → `_on_slab_selected` (update 3D viewer)
- `ScreeningDialog.load_surface` → `_load_from_screening` (load surface from screening)

### ui/viewer_widget.py — StructureViewer

Embeddable QWidget wrapping a matplotlib 3D figure.

- `FigureCanvasQTAgg` + `NavigationToolbar2QT`
- `.update_structure(structure)` — replot with new structure
- `.clear()` — show "No structure loaded" placeholder

### ui/screening_dialog.py — ScreeningDialog + ScreeningWorker

- `ScreeningWorker(QThread)` — runs `SurfaceScreener.screen()` in background
  - Signals: `progress(int, int)`, `finished(list)`, `error(str)`
- `ScreeningDialog(QDialog)` — parameter inputs, progress bar, QTableWidget
  - Signal: `load_surface(slab, miller_tuple)` — emitted when user clicks "Load in Main"
  - Color-codes rows: green = symmetric, yellow = asymmetric
  - CSV export via Python `csv` module

### ui/dft_dialog.py — DFTInputDialog

- Configuration spinboxes/combos for VASP parameters
- Live INCAR preview (QTextEdit, updates on any parameter change)
- Calls `DFTInputGenerator.generate()` to write files to user-selected directory

---

## Key Dependencies

| Library | Used For |
|---------|----------|
| pymatgen | Structure, Slab, SlabGenerator, Poscar, Incar, Kpoints, CifWriter, StructureMatcher, Element |
| mp-api | MPRester for Materials Project queries |
| PyQt5 | GUI framework |
| matplotlib | 3D structure visualization (FigureCanvasQTAgg) |
| numpy | Coordinate transformations |

---

## Data Flow

```
User Input
    │
    ├── MP Search ──→ MPRester.materials.search() ──→ structure_docs list
    │                                                      │
    └── File Upload ──→ Structure.from_file() ──→ local_structure
                                                      │
                                              _get_chosen_structure()
                                                      │
                    ┌─────────────────────────────────┤
                    │                                  │
            Generate Slabs                    Screen All Surfaces
                    │                                  │
        oriented_slab_replication()          SurfaceScreener.screen()
                    │                                  │
            generated_slabs list              results table + CSV
                    │
        ┌───────────┼───────────┐
        │           │           │
    3D Viewer    Export     DFT Inputs
        │        (VASP/CIF)     │
   plot_structure_3d()     DFTInputGenerator.generate()
                                │
                    POSCAR + INCAR + KPOINTS + job.sh
```
