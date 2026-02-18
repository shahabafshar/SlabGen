# SlabGen Demo

Scripts and outputs for demonstrating SlabGen's features using alpha-Mo2C (mp-1552) as the case study.

## Structure

```text
demo/
├── README.md                          # This file
├── scripts/
│   ├── capture_gui_screenshots_v2.py  # Automated GUI screenshot capture (signal-based)
│   ├── quick_demo.py                  # Programmatic demo (no GUI needed)
│   ├── generate_poster.py             # GPSS conference poster (48x36 PPTX)
│   ├── generate_presentation.py       # GPSS presentation slides (13 slides, 16:9 PPTX)
│   ├── demo_workflow.py               # Full demo with MP API integration
│   ├── capture_gui_screenshots.py     # GUI screenshot capture (v1, legacy)
│   └── capture_dialogs.py             # Dialog-only capture (legacy)
└── output/                            # All generated outputs
    ├── gui_screenshots/               # 11 GUI screenshots (01-11)
    ├── *.png                          # 3D visualizations from quick_demo
    ├── screening_results.csv          # Screening results (20 terminations, 7 surfaces)
    ├── all_slabs/                     # Exported POSCAR files (Mo2C 1,1,1 terminations)
    ├── dft_inputs_Mo2C_111/           # Generated DFT input set (INCAR, KPOINTS, POSCAR, etc.)
    ├── GPSS_poster_SlabGen.pptx       # Conference poster
    └── GPSS_presentation_SlabGen.pptx # Presentation slides
```

## Quick Start

### Capture GUI screenshots (recommended)

```bash
python demo/scripts/capture_gui_screenshots_v2.py
```

Automatically walks through the full Mo2C workflow and captures 11 screenshots showing each stage: startup, MP search, structure selection, slab generation with (1,1,1) Miller indices (6 terminations), surface screening (20 terminations across 7 orientations), and DFT input generation. Uses the Materials Project API to fetch mp-1552. Saves to both `demo/output/gui_screenshots/` and `demo_output/gui_screenshots/`.

### Run programmatic demo

```bash
python demo/scripts/quick_demo.py
```

Generates 3D visualizations, screening CSV, slab POSCAR exports, and DFT input files for Mo2C (1,1,1) without the GUI. Requires an MP API key in `mp_api_key.txt`.

### Generate conference materials

```bash
# GPSS conference poster (48x36 inches, ISU branding)
python demo/scripts/generate_poster.py

# GPSS presentation slides (13 slides, 16:9 widescreen)
python demo/scripts/generate_presentation.py
```

Both scripts embed GUI screenshots and screening data into PowerPoint files with Iowa State University cardinal/gold branding.

## Case Study: Mo2C

All demo scripts use alpha-Mo2C (mp-1552, Pbcn, orthorhombic, 12 atoms):

- **(1,1,1) surface**: 6 unique terminations, 36 atoms each, 49.20 A^2 surface area
- **Full screening** (max Miller index 1): 20 terminations across 7 surface orientations, 10 symmetric + 10 asymmetric
- **DFT inputs**: INCAR with auto dipole correction, KPOINTS with k_z=1, SLURM job script

## Documentation

See [../FEATURE_DEMONSTRATION.md](../FEATURE_DEMONSTRATION.md) for the complete walkthrough with all screenshots.
