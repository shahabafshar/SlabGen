from pymatgen.core.surface import get_symmetrically_distinct_miller_indices
from core.slab_generator import oriented_slab_replication


class SurfaceScreener:
    """Systematically screen all unique Miller index surfaces for a structure."""

    def __init__(self, structure, max_index, z_reps, vacuum,
                 center_slab, force_ortho):
        self.structure = structure
        self.max_index = max_index
        self.z_reps = z_reps
        self.vacuum = vacuum
        self.center_slab = center_slab
        self.force_ortho = force_ortho

    def screen(self, progress_callback=None):
        """
        Generate all symmetrically distinct surfaces up to max_index.

        Args:
            progress_callback: callable(current, total) for progress updates

        Returns:
            list of dicts with screening results for each slab/termination
        """
        miller_indices = get_symmetrically_distinct_miller_indices(
            self.structure, self.max_index
        )
        total = len(miller_indices)
        results = []
        failures = []

        for idx, (h, k, l) in enumerate(miller_indices):
            if progress_callback:
                progress_callback(idx, total)

            try:
                slabs = oriented_slab_replication(
                    structure=self.structure.copy(),
                    h=h, k=k, l=l,
                    z_reps=self.z_reps,
                    min_vac=self.vacuum,
                    center_slab=self.center_slab,
                    all_terminations=True,
                    force_ortho=self.force_ortho,
                )
            except Exception as e:
                failures.append({"miller": (h, k, l), "error": str(e)})
                continue

            for slab in slabs:
                shift_val = getattr(slab, "shift", 0.0)
                try:
                    is_sym = slab.is_symmetric()
                except Exception:
                    is_sym = None

                results.append({
                    "miller": (h, k, l),
                    "miller_str": f"({h},{k},{l})",
                    "shift": round(shift_val, 4),
                    "num_atoms": len(slab),
                    "surface_area": round(slab.surface_area, 2),
                    "is_symmetric": is_sym,
                    "formula": slab.composition.reduced_formula,
                    "slab": slab,
                })

        if progress_callback:
            progress_callback(total, total)

        # Attach failure info so callers can report it
        self.failures = failures

        return results
