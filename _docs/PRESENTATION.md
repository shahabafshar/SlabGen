# SlabGen: Systematic Surface Generation, Screening, and DFT Preparation

Shahab Afsharghoochani and Zeinab H. Fard
Iowa State University, Materials Science and Engineering

14th Annual GPSS Research Conference | February 20, 2026

<!-- 5 min rapid fire | max 5 slides including this one | no Q&A | use --- as slide breaks -->

---

## The Problem

Surfaces govern much of how materials interact with their environment, including catalytic activity, corrosion, coatings, and film growth.

Studying surfaces from first principles means building slab models: periodic structures cut from a bulk crystal along a chosen plane, then relaxed with DFT. The idea is straightforward. **The practical workflow is not.**

- Each material and orientation demands its own script
- Unphysical polar terminations and missing surface cuts go unnoticed
- Geometric distortion at high-index planes
- Fragmented toolchain: Materials Project → pymatgen scripts → VESTA → manual VASP input prep

<!-- VISUAL: Side-by-side. Messy Python terminal on the left, SlabGen screenshot on the right -->

---

## SlabGen

An open-source GUI that handles the full surface workflow in one place.

<!-- VISUAL: Full-window screenshot of SlabGen with a Mo2C slab in the 3D viewer. Annotate the key regions. -->

**Load** a crystal from the Materials Project or a local file
**Generate** slabs for any Miller index using a two-step orient-then-replicate strategy that avoids distortion
**Visualize** in interactive 3D: rotate, zoom, compare terminations
**Screen** all symmetrically distinct orientations at once. Catalogs every termination, flags symmetric vs. asymmetric
**Prepare** ready-to-submit VASP file sets (INCAR, KPOINTS, POSCAR, job script) with automatic dipole corrections

Built with Python, PySide6, and pymatgen. Open source, MIT license.

---

## Case Study: Pt Validation + Mo₂C

<!-- VISUAL: Left side: Pt surface energy bar chart vs. literature values. Right side: Mo2C screening table showing 44 terminations, plus 2-3 3D slab renders. -->

**Platinum (validation):**

- Predicted surface energy ordering γ(111) < γ(100) < γ(110), consistent with experiment and prior computational work
- 9 orientations, 1 termination each, all symmetric, as expected for FCC

**Mo₂C (where SlabGen's screening power matters):**

- **19** orientations, **44** unique terminations: 34 symmetric, 10 asymmetric
- (1,1,1) alone has 6 distinct terminations. The Miller index doesn't fully define a surface
- All 44 terminations screened and VASP inputs generated in a single interactive session

Surface energy: $\gamma = (E_{slab} - n \cdot E_{bulk}) \;/\; 2A$

---

## Takeaway

**SlabGen turns days of scripting into minutes of guided interaction.**

It makes systematic surface studies practical. Screen every surface of a material, visualize them, and go straight to DFT, all without writing a single line of code.

**Open source:** github.com/shahabafshar/SlabGen

<!-- VISUAL: QR code to GitHub + ISU logo -->

Thank you.
