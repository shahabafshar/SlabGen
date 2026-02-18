"""
Quick demonstration script - generates key outputs for documentation.
Uses alpha-Mo2C (mp-1552, Pbcn, orthorhombic, 12 atoms) from Materials Project.
Falls back to a synthetic Mo2C if no API key is available.
"""
import sys
import csv
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from pymatgen.core import Structure, Lattice
from core.slab_generator import oriented_slab_replication
from core.screening import SurfaceScreener
from core.dft_inputs import DFTInputGenerator
from core.visualization import plot_structure_3d
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

script_dir = Path(__file__).parent
output_dir = script_dir.parent / "output"
output_dir.mkdir(parents=True, exist_ok=True)


def fetch_mo2c():
    """Try to fetch mp-1552 (alpha-Mo2C) from Materials Project."""
    api_key_file = project_root / "mp_api_key.txt"
    if not api_key_file.exists():
        return None
    try:
        from mp_api.client import MPRester
        api_key = api_key_file.read_text().strip()
        with MPRester(api_key) as mpr:
            doc = mpr.materials.get_structure_by_material_id("mp-1552")
            print("   Fetched mp-1552 (alpha-Mo2C, Pbcn) from Materials Project")
            return doc
    except Exception as e:
        print(f"   MP fetch failed ({e}), using synthetic fallback")
        return None


def synthetic_mo2c():
    """Synthetic alpha-Mo2C approximation (orthorhombic, 12 atoms)."""
    lattice = Lattice.orthorhombic(4.724, 6.004, 5.199)
    species = ["Mo"] * 8 + ["C"] * 4
    coords = [
        [0.25, 0.12, 0.08], [0.75, 0.88, 0.92],
        [0.25, 0.62, 0.42], [0.75, 0.38, 0.58],
        [0.25, 0.88, 0.58], [0.75, 0.12, 0.42],
        [0.25, 0.38, 0.92], [0.75, 0.62, 0.08],
        [0.0, 0.35, 0.25], [0.5, 0.65, 0.75],
        [0.0, 0.85, 0.75], [0.5, 0.15, 0.25],
    ]
    print("   Using synthetic alpha-Mo2C (Pbcn-like, 12 atoms)")
    return Structure(lattice, species, coords)


print("=" * 60)
print("SlabGen Demo: alpha-Mo2C (mp-1552)")
print("=" * 60)

# Get structure
print("\n1. Loading Mo2C structure...")
structure = fetch_mo2c() or synthetic_mo2c()
print(f"   {structure.composition.reduced_formula}, "
      f"{len(structure)} atoms, "
      f"lattice: {structure.lattice.a:.2f} x {structure.lattice.b:.2f} x {structure.lattice.c:.2f} A")

# Bulk visualization
print("\n2. Visualizing bulk structure...")
fig = plt.figure(figsize=(8, 8))
ax = fig.add_subplot(111, projection='3d')
plot_structure_3d(ax, structure)
plt.title("Bulk Structure: alpha-Mo2C (mp-1552)", fontsize=14, fontweight='bold')
plt.savefig(output_dir / "01_bulk_structure.png", dpi=150, bbox_inches='tight')
plt.close()
print(f"   Saved: 01_bulk_structure.png")

# Generate (1,1,1) slabs
print("\n3. Generating (1,1,1) slabs...")
slabs = oriented_slab_replication(
    structure=structure.copy(),
    h=1, k=1, l=1,
    z_reps=3,
    min_vac=15.0,
    center_slab=False,
    all_terminations=True,
    force_ortho=False,
)
print(f"   Generated {len(slabs)} slab(s)")

if slabs:
    slab = slabs[0]
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    plot_structure_3d(ax, slab)
    shift_val = getattr(slab, "shift", 0.0)
    plt.title(f"Mo2C Slab (1,1,1) - Shift: {shift_val:.4f}\n"
              f"Atoms: {len(slab)}, Area: {slab.surface_area:.2f} A^2",
              fontsize=14, fontweight='bold')
    plt.savefig(output_dir / "02_generated_slab.png", dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   Saved: 02_generated_slab.png")

# Surface screening
print("\n4. Screening surfaces (max_index=1)...")
screener = SurfaceScreener(
    structure=structure.copy(),
    max_index=1,
    z_reps=3,
    vacuum=15.0,
    center_slab=False,
    force_ortho=False,
)
results = screener.screen()
print(f"   Found {len(results)} terminations")

# CSV export
csv_path = output_dir / "screening_results.csv"
with open(csv_path, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Miller Index', 'Shift', 'Atoms', 'Surface Area (A^2)', 'Symmetric', 'Formula'])
    for r in results:
        writer.writerow([
            r['miller_str'], r['shift'], r['num_atoms'],
            f"{r['surface_area']:.2f}", r['is_symmetric'], r['formula']
        ])
print(f"   Saved: screening_results.csv")

# Surface visualization grid
if len(results) >= 2:
    fig, axes = plt.subplots(2, 2, figsize=(16, 16), subplot_kw={'projection': '3d'})
    axes = axes.flatten()
    unique = {}
    for r in results:
        ms = r['miller_str']
        if ms not in unique:
            unique[ms] = r['slab']
            if len(unique) >= 4:
                break

    surface_list = list(unique.items())
    for idx in range(4):
        i = idx % len(surface_list)
        ms, surf = surface_list[i]
        plot_structure_3d(axes[idx], surf)
        axes[idx].set_title(f"Surface {ms}\n"
                            f"Atoms: {len(surf)}, Area: {surf.surface_area:.2f} A^2",
                            fontsize=10, fontweight='bold')

    plt.suptitle("Mo2C Surface Screening Results", fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.savefig(output_dir / "03_surface_screening.png", dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   Saved: 03_surface_screening.png")

# DFT inputs
if slabs:
    print("\n5. Generating DFT inputs...")
    slab = slabs[0]
    generator = DFTInputGenerator(slab)
    config = {
        "encut": 400,
        "k_product": 50,
        "isif": 2,
        "ismear": 0,
        "sigma": 0.05,
        "ediffg": -0.02,
        "auto_dipole": True,
        "job_name": "Mo2C_111_relax",
    }
    dft_dir = output_dir / "dft_inputs_Mo2C_111"
    paths = generator.generate(dft_dir, config)
    print(f"   Generated in: dft_inputs_Mo2C_111/")
    for name in paths:
        print(f"     - {name}")

# Export slabs
if slabs:
    print("\n6. Exporting slabs...")
    from pymatgen.io.vasp.inputs import Poscar
    export_dir = output_dir / "all_slabs"
    export_dir.mkdir(exist_ok=True)
    for slab in slabs:
        shift_val = getattr(slab, "shift", 0.0)
        fname = f"POSCAR_Mo2C_1-1-1_shift{shift_val:.4f}.vasp"
        Poscar(slab).write_file(export_dir / fname)
    print(f"   Exported {len(slabs)} slab(s) to: all_slabs/")

print("\n" + "=" * 60)
print(f"Demo complete! Outputs in: {output_dir.absolute()}")
print("=" * 60)
