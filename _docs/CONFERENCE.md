# GPSS Conference Prep

14th Annual GPSS Research Conference — February 20, 2026
Great Hall, Memorial Union, Iowa State University (8 AM – 3 PM)
Awards ceremony: Feb 24, 6–8 PM, South Ballroom
Entering both oral and poster competitions.

---

## Abstract

**SlabGen: An Integrated Platform for Systematic Surface Generation, Visualization, and DFT Workflow Preparation**

Shahab Afsharghoochani and Zeinab Hajali Fard, Iowa State University

Surface slab generation is a critical step in computational surface science, underpinning studies of catalysis, corrosion, thin films, and crystal growth. Researchers typically generate surface structures through manual scripting, a process that requires expertise in crystallographic transformations and is prone to errors such as incorrect terminations, polar surfaces, and atom stretching artifacts at high-index orientations. We present SlabGen, an open-source graphical platform that integrates the full surface science workflow: structure sourcing from the Materials Project database or local files (VASP, CIF), slab generation using a robust two-step orient-then-replicate algorithm, interactive 3D visualization, systematic screening of all symmetrically distinct surfaces, and automated preparation of density functional theory (DFT) input files. SlabGen's screening engine identifies all unique Miller index surfaces up to a user-specified maximum, catalogs their terminations, and reports symmetry properties, enabling researchers to systematically survey a material's surface landscape in minutes rather than hours. We demonstrate SlabGen's capabilities through a case study on Mo2C, a material of interest for catalysis and hard coating applications, where we screen all low-index surfaces, identify symmetric and asymmetric terminations, and prepare VASP input sets for surface energy calculations. SlabGen is built with Python, PyQt5, and pymatgen, and is freely available on GitHub.

---

## Talk Outline (10–12 minutes)

The talk has three acts: why this matters, what we built, and what we found.

**Slide 1 — Title**
Standard title slide. Names, Iowa State affiliation. Maybe a one-liner connecting to the conference theme.

**Slide 2 — Motivation (2 min)**
Open with why surfaces matter — catalysis, corrosion, coatings, crystal growth. Then explain the pain: right now, generating slabs means writing pymatgen scripts by hand. That's slow, error-prone, and you can easily end up with wrong terminations, polar surfaces, or stretched atoms at high-index orientations. The real gap is that no single tool connects the full pipeline from structure sourcing through screening, visualization, and DFT prep.

**Slide 3 — SlabGen Overview (1 min)**
Show a simple architecture diagram: Materials Project or local file goes in, slab generation happens, then you can visualize in 3D, screen all surfaces, and generate DFT inputs. Mention it's open source and cross-platform. The key technical contribution is the two-step orient-then-replicate algorithm.

**Slide 4 — The Two-Step Algorithm (1 min)**
A diagram explaining the approach:
1. Orient the bulk crystal so (h,k,l) aligns with z, then replicate along z
2. Apply SlabGenerator with (0,0,1) to add vacuum and enumerate terminations

This avoids the distortion artifacts you get from directly generating high-index slabs.

**Slide 5 — Live Demo (3 min)**
Walk through the full workflow live:
- Search "Mo2C" in the Materials Project panel, select a structure, see it in the 3D viewer
- Set Miller index to (001), hit Generate, rotate the slab around
- Open "Screen All Surfaces," watch the progress bar, look at the results table
- Pick an interesting surface, load it back into the main window
- Open "Prepare DFT Inputs," show the INCAR preview, generate files

Have a pre-recorded backup video and static screenshots ready in case anything goes wrong.

**Slide 6 — Case Study: Mo2C (1 min)**
Why Mo2C — it's relevant for catalysis and hard coatings. We screened all surfaces up to max Miller index 2 and selected 3–5 for DFT relaxation.

**Slide 7 — Screening Results (1 min)**
Show the full screening table: all Mo2C surfaces, number of terminations per Miller index, which are symmetric vs. asymmetric. Highlight anything surprising — which surfaces have the most terminations, which are polar.

**Slide 8 — DFT Results (2 min)**
Surface energies for the selected surfaces, reported in both eV/A^2 and J/m^2. Show the formula (gamma = (E_slab - n * E_bulk) / (2A)), then a bar chart comparing surfaces. If we have it ready, show the Wulff construction — the predicted equilibrium crystal shape.

**Slide 9 — Impact and Future Work (1 min)**
What this enables: systematic surface studies that used to take weeks of scripting now take minutes. It's open source (MIT license) on GitHub. Future directions: a surface energy database, adsorption site identification, support for codes beyond VASP.

**Slide 10 — Acknowledgments**
Collaborators, funding, ISU resources. GitHub link with a QR code so people can find it.

---

## Poster

Standard 48" x 36" landscape research poster. The layout roughly follows this flow:

```
+----------------------------------------------------+
|                    TITLE BAR                        |
|  SlabGen: An Integrated Platform for Systematic    |
|  Surface Generation, Visualization, and DFT        |
|  Workflow Preparation                               |
|  S. Afsharghoochani, Z. Hajali Fard — Iowa State   |
+----------+----------+----------+-------------------+
|          |          |          |                    |
| PROBLEM  | APPROACH | FEATURES |   SCREENSHOT       |
|          |          |          |   (main window     |
| Why      | Two-step | 3D       |    with 3D viewer  |
| surfaces | orient-  | viewer,  |    showing a Mo2C  |
| matter,  | then-    | screen-  |    slab)           |
| manual   | replicate| ing, DFT |                    |
| workflow | algorithm| inputs,  |                    |
| problems |          | CIF/VASP |                    |
+----------+----+-----+----------+-------------------+
|                |                                    |
|  WORKFLOW      |    CASE STUDY: Mo2C                |
|  DIAGRAM       |                                    |
|  MP/File ->    |  Screening results table           |
|  Generate ->   |  Surface energy bar chart          |
|  Screen ->     |  3D renders of key surfaces        |
|  Visualize ->  |  Wulff construction (if ready)     |
|  DFT           |                                    |
+----------------+------------------------------------+
|  CONCLUSIONS   |  REFERENCES / QR CODE              |
|  & FUTURE WORK |  github.com/shahabafshar/SlabGen   |
+----------------+------------------------------------+
```

**Visuals to prepare:**
- [ ] Full-window screenshot of SlabGen with Mo2C slab in the 3D viewer
- [ ] Workflow diagram (PowerPoint or Inkscape)
- [ ] 3D renders of 3–5 Mo2C surfaces (screenshots from the viewer)
- [ ] Screening results table (formatted from CSV export)
- [ ] Surface energy bar chart (matplotlib or Excel)
- [ ] Wulff construction figure (stretch goal — use pymatgen's WulffShape)
- [ ] QR code to the GitHub repo
- [ ] ISU and department logos

---

## Mo2C Case Study

This is what turns the presentation from a tool demo into a research contribution.

### Steps

- [ ] Load Mo2C from Materials Project (mp-1552 or mp-14181)
- [ ] Run batch screening with max_index=2
- [ ] Export screening results to CSV
- [ ] Screenshot the screening table
- [ ] Screenshot 3–5 key surfaces in the 3D viewer
- [ ] Generate DFT inputs for 3–5 selected surfaces
- [ ] Generate a bulk Mo2C reference calculation (ISIF=3 for full cell relaxation)
- [ ] Submit everything to HPC
- [ ] Collect total energies from VASP OUTCAR/OSZICAR
- [ ] Calculate surface energies
- [ ] Create a comparison chart
- [ ] Generate Wulff construction plot (stretch goal)

### Surface Energy Formula

    gamma = (E_slab - n * E_bulk) / (2 * A)

    E_slab  = total energy of the relaxed slab (from OSZICAR)
    E_bulk  = total energy per formula unit of bulk Mo2C
    n       = number of formula units in the slab
    A       = surface area in Angstrom^2 (from the screening table)
    The factor of 2 accounts for the slab having two exposed surfaces.

    To convert from eV/A^2 to J/m^2, multiply by 16.02.
    For reference, carbide surface energies typically fall in the 1.0–4.0 J/m^2 range.

### Wulff Construction

If we get surface energies in time, we can build a Wulff shape to predict the equilibrium crystal morphology:

```python
from pymatgen.analysis.wulff import WulffShape

miller_list = [(0,0,1), (1,0,0), (1,1,0), (1,1,1)]
energy_list = [gamma_001, gamma_100, gamma_110, gamma_111]  # J/m^2

lattice = bulk_structure.lattice
wulff = WulffShape(lattice, miller_list, energy_list)

fig = wulff.get_plot()
fig.savefig("wulff_Mo2C.png", dpi=300)

for facet in wulff.area_fraction_dict:
    print(f"{facet}: {wulff.area_fraction_dict[facet]:.3f}")
```

---

## Backup Plan

If something goes wrong:

- **Live demo fails**: Switch to the pre-recorded video or static screenshots.
- **DFT jobs not done by Feb 18**: Focus the talk on the tool itself and the screening results. Show that jobs were submitted as proof the workflow is complete end-to-end. Frame surface energies as "ongoing work."

---

## Timeline

| Date | What to do |
|------|------------|
| Feb 9 | Submit abstract |
| Feb 10–12 | Run Mo2C screening, capture all screenshots |
| Feb 12–14 | Submit DFT jobs to HPC |
| Feb 15 | Collect DFT results (if finished) |
| Feb 16–17 | Build slides and poster |
| Feb 18–19 | Practice the talk — at least 3 full run-throughs |
| Feb 20 | Conference day |
