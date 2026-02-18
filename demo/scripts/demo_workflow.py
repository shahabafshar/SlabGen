"""
Demonstration script that showcases all major features of SlabGen.
This script exercises the core functionality programmatically.
"""
import os
import sys
from pathlib import Path

# Add project root to path (go up two levels from scripts folder)
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

from pymatgen.core import Structure
from mp_api.client import MPRester
from core.slab_generator import oriented_slab_replication
from core.screening import SurfaceScreener
from core.dft_inputs import DFTInputGenerator
from core.visualization import plot_structure_3d
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

# Read API key (from project root)
api_key_path = project_root / "mp_api_key.txt"
if api_key_path.exists():
    with open(api_key_path) as f:
        API_KEY = f.read().strip()
else:
    API_KEY = None
    print("Warning: No API key found. Using example structure instead.")

def demo_workflow():
    """Complete workflow demonstration."""
    print("=" * 80)
    print("SlabGen Complete Feature Demonstration")
    print("=" * 80)
    
    # Create output directory (relative to script location)
    output_dir = script_dir.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # ========================================================================
    # FEATURE 1: Materials Project Search
    # ========================================================================
    print("\n[1] Materials Project Search")
    print("-" * 80)
    
    if API_KEY:
        try:
            with MPRester(API_KEY) as mpr:
                docs = mpr.materials.search(formula="TiO2", num_elements=2)
                if docs:
                    doc = docs[0]
                    structure = doc.structure
                    material_id = doc.material_id
                    formula = doc.formula_pretty
                    print(f"[OK] Found: {material_id} - {formula}")
                    print(f"  Space Group: {doc.symmetry.symbol}")
                    print(f"  Crystal System: {doc.symmetry.crystal_system}")
                    print(f"  Atoms: {len(structure)}")
                else:
                    raise ValueError("No results found")
        except Exception as e:
            print(f"[ERROR] MP API search failed: {e}")
            print("  Using example TiO2 structure instead...")
            # Create example TiO2 structure
            structure = Structure.from_file("https://materialsproject.org/materials/mp-2657/")
            material_id = "mp-2657"
            formula = "TiO2"
    else:
        # Use a simple example structure
        from pymatgen.core import Lattice
        lattice = Lattice.cubic(4.0)
        species = ["Ti", "O", "O"]
        coords = [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0.5, 0]]
        structure = Structure(lattice, species, coords)
        material_id = "DEMO"
        formula = "TiO2"
        print(f"[OK] Using demo structure: {formula}")
    
    # Visualize bulk structure
    print("\n[2] 3D Visualization of Bulk Structure")
    print("-" * 80)
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection='3d')
    plot_structure_3d(ax, structure)
    plt.title(f"Bulk Structure: {formula} ({material_id})")
    bulk_viz_path = output_dir / "01_bulk_structure.png"
    plt.savefig(bulk_viz_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[OK] Saved bulk visualization: {bulk_viz_path}")
    
    # ========================================================================
    # FEATURE 3: Slab Generation
    # ========================================================================
    print("\n[3] Slab Generation")
    print("-" * 80)
    
    h, k, l = 1, 0, 1  # (101) surface
    z_reps = 3
    vacuum = 15.0
    center_slab = False
    all_terminations = True
    force_ortho = False
    
    print(f"  Generating ({h},{k},{l}) slabs...")
    print(f"  Parameters: z_reps={z_reps}, vacuum={vacuum} Å")
    
    slabs = oriented_slab_replication(
        structure=structure.copy(),
        h=h, k=k, l=l,
        z_reps=z_reps,
        min_vac=vacuum,
        center_slab=center_slab,
        all_terminations=all_terminations,
        force_ortho=force_ortho,
    )
    
    print(f"[OK] Generated {len(slabs)} slab termination(s)")
    
    # Visualize first slab
    if slabs:
        slab = slabs[0]
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        plot_structure_3d(ax, slab)
        shift_val = getattr(slab, "shift", 0.0)
        plt.title(f"Slab ({h},{k},{l}) - Shift: {shift_val:.4f}\n"
                 f"Atoms: {len(slab)}, Area: {slab.surface_area:.2f} Å²")
        slab_viz_path = output_dir / "02_generated_slab.png"
        plt.savefig(slab_viz_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"[OK] Saved slab visualization: {slab_viz_path}")
        
        # Export slab
        from pymatgen.io.vasp.inputs import Poscar
        slab_export_path = output_dir / f"POSCAR_{material_id}_{h}-{k}-{l}_z{z_reps}_vac{vacuum}_shift{shift_val:.4f}.vasp"
        Poscar(slab).write_file(slab_export_path)
        print(f"[OK] Exported slab: {slab_export_path.name}")
    
    # ========================================================================
    # FEATURE 4: Surface Screening
    # ========================================================================
    print("\n[4] Surface Screening")
    print("-" * 80)
    
    max_index = 2
    print(f"  Screening all surfaces up to Miller index {max_index}...")
    
    screener = SurfaceScreener(
        structure=structure.copy(),
        max_index=max_index,
        z_reps=z_reps,
        vacuum=vacuum,
        center_slab=center_slab,
        force_ortho=force_ortho,
    )
    
    def progress_callback(current, total):
        if current % max(1, total // 10) == 0 or current == total:
            print(f"  Progress: {current}/{total} surfaces")
    
    results = screener.screen(progress_callback=progress_callback)
    
    print(f"[OK] Screened {len(results)} terminations across {len(set(r['miller_str'] for r in results))} unique surfaces")
    
    # Export screening results to CSV
    import csv
    csv_path = output_dir / "screening_results.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Miller Index', 'Shift', 'Atoms', 'Surface Area (Å²)', 'Symmetric', 'Formula'])
        for r in results:
            writer.writerow([
                r['miller_str'], r['shift'], r['num_atoms'],
                r['surface_area'], r['is_symmetric'], r['formula']
            ])
    print(f"[OK] Exported screening results: {csv_path}")
    
    # Visualize a few different surfaces
    unique_surfaces = {}
    for r in results:
        miller_str = r['miller_str']
        if miller_str not in unique_surfaces:
            unique_surfaces[miller_str] = r['slab']
            if len(unique_surfaces) >= 4:  # Show first 4 unique surfaces
                break
    
    if unique_surfaces:
        fig, axes = plt.subplots(2, 2, figsize=(16, 16), subplot_kw={'projection': '3d'})
        axes = axes.flatten()
        for idx, (miller_str, surf_slab) in enumerate(unique_surfaces.items()):
            if idx < 4:
                plot_structure_3d(axes[idx], surf_slab)
                axes[idx].set_title(f"Surface {miller_str}\n"
                                  f"Atoms: {len(surf_slab)}, Area: {surf_slab.surface_area:.2f} Å²",
                                  fontsize=10)
        plt.tight_layout()
        screening_viz_path = output_dir / "03_surface_screening.png"
        plt.savefig(screening_viz_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"[OK] Saved screening visualization: {screening_viz_path}")
    
    # ========================================================================
    # FEATURE 5: DFT Input Generation
    # ========================================================================
    print("\n[5] DFT Input Generation")
    print("-" * 80)
    
    if slabs:
        slab = slabs[0]
        generator = DFTInputGenerator(slab)
        
        config = {
            "encut": 400,
            "k_product": 50,
            "isif": 2,  # Relax ions only
            "ismear": 0,
            "sigma": 0.05,
            "ediffg": -0.02,
            "auto_dipole": True,
            "job_name": f"{material_id}_{h}{k}{l}_relax",
        }
        
        dft_output_dir = output_dir / f"dft_inputs_{material_id}_{h}{k}{l}"
        paths = generator.generate(dft_output_dir, config)
        
        print(f"[OK] Generated DFT inputs in: {dft_output_dir}")
        for name, path in paths.items():
            print(f"  - {name}")
        
        # Show INCAR preview
        incar_preview = generator.get_incar_preview(config)
        print("\n  INCAR Preview:")
        print("  " + "-" * 76)
        for line in incar_preview.split('\n')[:15]:  # Show first 15 lines
            print(f"  {line}")
        print("  " + "-" * 76)
    
    # ========================================================================
    # FEATURE 6: Export All Slabs
    # ========================================================================
    print("\n[6] Export All Slabs")
    print("-" * 80)
    
    if slabs:
        export_dir = output_dir / "all_slabs"
        export_dir.mkdir(exist_ok=True)
        
        from pymatgen.io.vasp.inputs import Poscar
        exported = []
        for i, slab in enumerate(slabs):
            shift_val = getattr(slab, "shift", i)
            fname = f"POSCAR_{material_id}_{h}-{k}-{l}_shift{shift_val:.4f}.vasp"
            fpath = export_dir / fname
            Poscar(slab).write_file(fpath)
            exported.append(fname)
        
        print(f"[OK] Exported {len(exported)} slabs to: {export_dir}")
        for fname in exported[:5]:  # Show first 5
            print(f"  - {fname}")
        if len(exported) > 5:
            print(f"  ... and {len(exported) - 5} more")
    
    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "=" * 80)
    print("Demonstration Complete!")
    print("=" * 80)
    print(f"\nAll outputs saved to: {output_dir.absolute()}")
    print("\nGenerated files:")
    for file in sorted(output_dir.rglob("*")):
        if file.is_file():
            rel_path = file.relative_to(output_dir)
            size = file.stat().st_size
            print(f"  - {rel_path} ({size:,} bytes)")

if __name__ == "__main__":
    demo_workflow()
