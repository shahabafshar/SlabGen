import numpy as np
from pymatgen.core import Structure
from pymatgen.core.surface import SlabGenerator
from pymatgen.analysis.structure_matcher import StructureMatcher


def oriented_slab_replication(
    structure, h, k, l, z_reps, min_vac, center_slab,
    all_terminations, force_ortho
):
    """
    Two-stage slab generation:
    1) Orient bulk so (h,k,l) is along new z-axis (no vacuum, min_slab=1).
    2) Replicate oriented structure along new z by z_reps.
    3) Final SlabGenerator with (0,0,1), min_slab=1, min_vac, center_slab
       to produce vacuum and terminations.
    4) If force_ortho, apply get_orthogonal_c_slab().

    Returns a list of Slab objects.
    """
    # Step 1: orient along (h,k,l)
    orient_gen = SlabGenerator(
        initial_structure=structure.copy(),
        miller_index=(h, k, l),
        min_slab_size=1.0,
        min_vacuum_size=0.0,
        center_slab=False
    )
    oriented_slab = orient_gen.get_slab()

    # Step 2: replicate in z
    oriented_slab.make_supercell([1, 1, z_reps])

    # Step 3: add vacuum and terminations via (0,0,1) slab
    final_gen = SlabGenerator(
        initial_structure=oriented_slab,
        miller_index=(0, 0, 1),
        min_slab_size=1.0,
        min_vacuum_size=min_vac,
        center_slab=center_slab
    )

    if all_terminations:
        slabs = final_gen.get_slabs(symmetrize=False)
    else:
        slabs = [final_gen.get_slab()]

    # Step 4: orthogonalize if requested
    if force_ortho:
        slabs = [s.get_orthogonal_c_slab() for s in slabs]

    return slabs


def cut_out_z_region(structure, zmin, zmax):
    """Return new Structure with sites having z in [zmin, zmax] (Cartesian)."""
    new_sites = [site for site in structure if zmin <= site.coords[2] <= zmax]
    if not new_sites:
        return None
    new_struct = Structure(lattice=structure.lattice, species=[], coords=[])
    for s in new_sites:
        new_struct.append(
            s.species, s.coords, coords_are_cartesian=True,
            properties=s.properties if s.properties else None,
        )
    return new_struct


def rotate_bottom_180(structure):
    """Rotate structure 180 deg around y-axis (flip upside down)."""
    rotation_matrix = np.array([
        [-1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, -1.0]
    ])
    new_struct = Structure(lattice=structure.lattice, species=[], coords=[])
    for site in structure:
        new_coords = rotation_matrix.dot(site.coords)
        new_struct.append(site.species, new_coords, coords_are_cartesian=True)
    return new_struct


def compare_structures(top_struct, bottom_struct):
    """
    Use StructureMatcher to check if top and bottom surfaces match.
    Returns (is_match: bool, rmsd: float or None).
    """
    if top_struct is None or bottom_struct is None:
        return (False, None)
    matcher = StructureMatcher(
        stol=0.5,
        angle_tol=5,
        primitive_cell=False,
        attempt_supercell=False
    )
    is_match = matcher.fit(top_struct, bottom_struct)
    if is_match:
        rmsd, max_dist = matcher.get_rms_dist(top_struct, bottom_struct)
        return (True, rmsd)
    return (False, None)


def extract_surface_regions(slab, compare_depth):
    """
    Extract top and bottom surface regions from a slab.
    Returns (top_struct, bottom_rotated) where bottom is rotated 180 deg.
    """
    all_z = [site.coords[2] for site in slab]
    z_min, z_max = min(all_z), max(all_z)
    top_struct = cut_out_z_region(slab, z_max - compare_depth, z_max)
    bottom_struct = cut_out_z_region(slab, z_min, z_min + compare_depth)
    bottom_rot = rotate_bottom_180(bottom_struct) if bottom_struct else None
    return top_struct, bottom_rot
