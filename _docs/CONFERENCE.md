# GPSS Conference Prep

14th Annual GPSS Research Conference — February 20, 2026
Great Hall, Memorial Union, Iowa State University (8 AM – 3 PM)
Awards ceremony: Feb 24, 6–8 PM, South Ballroom
Theme: "Bridging Science and Society: Research for the Evolving World"
Entering both oral and poster competitions.

---

## Oral Competition Rules

- **5 minutes**, strictly enforced — penalty for going over
- **Maximum 5 slides** (including the title slide)
- No questions after the talk
- Judging: **Content 40%, Presentation 60%** (stage presence, eye contact, enthusiasm, command of material)
- Recommendation: know your material cold, practice delivery more than content

---

## Abstract

See [ABSTRACT.md](ABSTRACT.md) — three paragraphs: problem, tool, case studies (Pt validation + Mo2C).

---

## Talk Structure (5 slides, 1 min each)

Since delivery is 60% of the score, the slides exist to support the speaker, not carry the content. Each slide should be mostly visual with minimal text. Speak naturally, don't read.

**Slide 1 — Title (30 sec)**
Name, affiliation, one sentence: "I'm going to show you a tool that takes the manual scripting out of computational surface science."

**Slide 2 — The Problem (1 min)**
Surfaces govern how materials interact with their environment — catalysis, corrosion, coatings, film growth. Quick, 15 seconds. Then the real point: the idea of cutting a slab is straightforward, but the practical workflow is not. Each material and orientation demands its own script. Subtle errors — polar terminations, missing surface cuts, geometric distortion — go unnoticed. The toolchain is fragmented: Materials Project, pymatgen scripts, VESTA, manual VASP prep, no unified interface. Visual: show this fragmented pipeline.

**Slide 3 — SlabGen (1.5 min)**
This is the core slide. Show an annotated screenshot of the full application. Walk through the workflow: load a structure, generate slabs, visualize in 3D, screen all symmetrically distinct orientations, generate ready-to-submit VASP file sets. Mention the two-step orient-then-replicate strategy in one sentence ("the bulk cell is reoriented so the target plane lies along z, and only then are vacuum and termination cuts applied — this avoids distortion at high-index surfaces"). Don't go deeper — let the visual do the talking.

**Slide 4 — Pt Validation + Mo₂C (1.5 min)**
Two-part slide. Left: Pt gives γ(111) < γ(100) < γ(110), consistent with experiment and prior computational work — the method is validated. Right: Mo₂C screening — 19 orientations, 44 terminations (34 symmetric, 10 asymmetric), (1,1,1) with 6 distinct terminations. The contrast is the point: Pt validates the workflow, Mo₂C demonstrates why the screening engine matters. "The Miller index alone doesn't fully define a surface." All 44 terminations were screened and VASP inputs generated in a single interactive session.

**Slide 5 — Takeaway (30 sec)**
One sentence: "SlabGen turns days of scripting into minutes." Open source, GitHub link, QR code. Thank you.

---

## Delivery Tips

The 60/40 split means presentation skills matter more than slide content.

- **Rehearse out loud** at least 5 times with a timer. Cut anything that pushes past 4:45.
- **Don't read from slides.** Know the flow by heart. Glance at the slide, then talk to the audience.
- **Speak slowly.** Five minutes feels short but rushing is the biggest mistake. Pause between slides.
- **Eye contact.** Pick three spots in the room and rotate between them.
- **Enthusiasm matters.** You built this tool — show that you're excited about it.
- **Have a strong opening line.** Don't start with "So, um, my name is..." — start with a hook about the problem or a bold claim.
- **Have a strong closing line.** End with the takeaway, not "so yeah, that's it."

---

## Poster

Standard 48" x 36" landscape. The poster can carry more detail than the talk — use it to show what you had to cut from 5 minutes.

```
+----------------------------------------------------+
|                    TITLE BAR                        |
|  SlabGen: An Integrated Platform for Surface Slab  |
|  Generation and DFT Workflow Preparation            |
|  S. Afsharghoochani, Z. Hajali Fard — Iowa State   |
+----------+----------+----------+-------------------+
|          |          |          |                    |
| PROBLEM  | APPROACH | FEATURES |   SCREENSHOT       |
|          |          |          |   (SlabGen with    |
| Why      | Two-step | 3D       |    Mo2C slab in    |
| surfaces | orient-  | viewer,  |    3D viewer)      |
| matter,  | then-    | screen-  |                    |
| manual   | replicate| ing, DFT |                    |
| workflow | algorithm| inputs,  |                    |
| problems |          | CIF/VASP |                    |
+----------+----+-----+----------+-------------------+
|                |                                    |
|  WORKFLOW      |    CASE STUDIES                    |
|  DIAGRAM       |                                    |
|  MP/File ->    |  Pt: validation (surface energies  |
|  Generate ->   |       vs. published benchmarks)    |
|  Screen ->     |  Mo2C: 19 orientations, 44         |
|  Visualize ->  |       terminations, screening      |
|  DFT           |       results table, 3D renders    |
+----------------+------------------------------------+
|  CONCLUSIONS   |  REFERENCES / QR CODE              |
|  & FUTURE WORK |  github.com/shahabafshar/SlabGen   |
+----------------+------------------------------------+
```

**Visuals to prepare:**

- [ ] Full-window screenshot of SlabGen with Mo2C slab in 3D viewer
- [ ] Workflow diagram (PowerPoint or Inkscape)
- [ ] 3D renders of 3–5 Mo2C surfaces
- [ ] Pt surface energy bar chart vs. literature values
- [ ] Mo2C screening results table (from CSV export)
- [ ] QR code to GitHub repo
- [ ] ISU and department logos

---

## Case Studies

### Pt — Validation

Platinum is the validation case. FCC, monatomic, well-studied surface energies. The goal is to confirm that SlabGen's workflow reproduces the known ordering γ(111) < γ(100) < γ(110).

| Property | Platinum (mp-126) |
|----------|-------------------|
| Structure | FCC, Fm-3m |
| Lattice parameter | 2.788 A |
| Unique orientations | 9 |
| Total terminations | 9 |
| Symmetric slabs | 9 (all) |
| Area range | 6.7 – 12.9 A^2 |

Published references: Pt(111) ~ 1.49 J/m^2, Pt(100) ~ 1.81 J/m^2, Pt(110) ~ 1.86 J/m^2 (Vitos et al. 1998)

Steps:

- [x] Load Pt (mp-126) from Materials Project
- [x] Run batch screening with max_index=2
- [x] Confirm: 9 orientations, 1 termination each, all symmetric
- [ ] Generate DFT inputs for (1,1,1), (1,1,0), (1,0,0)
- [ ] Generate bulk Pt reference (ISIF=3)
- [ ] Submit to HPC
- [ ] Compute surface energies and verify γ(111) < γ(100) < γ(110) ordering

### Mo2C — Complex Multi-Component Case

Mo₂C is where the tool earns its value. Orthorhombic, 12 atoms in the unit cell, multiple terminations per orientation, asymmetric slabs. Screening all 44 terminations and generating VASP inputs in a single interactive session — a task that would conventionally require individual scripts for each orientation and termination.

| Property | Mo2C (mp-1552) |
|----------|----------------|
| Structure | Orthorhombic, Pbcn |
| Lattice | 4.73 x 5.21 x 6.05 A |
| Unique orientations | 19 |
| Total terminations | 44 |
| Symmetric slabs | 34 |
| Asymmetric slabs | 10 |
| Area range | 24.6 – 49.2 A^2 |

Steps:

- [x] Load Mo2C (mp-1552) from Materials Project
- [x] Run batch screening with max_index=2
- [x] Confirm: 19 orientations, 44 terminations, 34 symmetric / 10 asymmetric
- [ ] Export screening results to CSV
- [ ] Screenshot screening table and 3–5 key surfaces
- [ ] Generate DFT inputs for selected surfaces
- [ ] Generate bulk Mo2C reference (ISIF=3)
- [ ] Submit to HPC
- [ ] Compute surface energies
- [ ] Create comparison chart
- [ ] Wulff construction (stretch goal)

### Surface Energy Formula

    gamma = (E_slab - n * E_bulk) / (2 * A)

    E_slab  = total energy of relaxed slab (OSZICAR)
    E_bulk  = total energy per formula unit (bulk) or per atom (elemental)
    n       = number of formula units (or atoms) in the slab
    A       = surface area in Angstrom^2 (from screening table)
    Factor 2 = two exposed surfaces

    eV/A^2 to J/m^2: multiply by 16.02

### Wulff Construction

```python
from pymatgen.analysis.wulff import WulffShape

miller_list = [(1,1,1), (1,1,0), (1,0,0)]
energy_list = [gamma_111, gamma_110, gamma_100]  # J/m^2

wulff = WulffShape(structure.lattice, miller_list, energy_list)
fig = wulff.get_plot()
fig.savefig("wulff.png", dpi=300)
```

---

## Backup Plan

- **DFT results not done by Feb 18:** The screening results are already strong on their own. 44 terminations for Mo2C is a concrete finding. Show that DFT inputs were generated and jobs submitted. The tool workflow is the main contribution.
- **Live demo fails at conference:** Use static screenshots and the pre-recorded workflow video.

---

## Timeline

| Date | What to do |
|------|------------|
| Feb 9 | Submit abstract |
| Feb 10–12 | Capture Pt and Mo2C screenshots, export CSVs |
| Feb 12–14 | Submit DFT jobs to HPC (Pt + Mo2C) |
| Feb 15 | Collect DFT results (if finished) |
| Feb 16–17 | Build 5 slides and poster |
| Feb 18–19 | Practice the talk — **5+ full timed run-throughs** |
| Feb 20 | Conference day |
