import numpy as np
from pymatgen.core import Element

# Jmol color scheme for common elements
JMOL_COLORS = {
    "H":  (1.000, 1.000, 1.000), "He": (0.851, 1.000, 1.000),
    "Li": (0.800, 0.502, 1.000), "Be": (0.761, 1.000, 0.000),
    "B":  (1.000, 0.710, 0.710), "C":  (0.565, 0.565, 0.565),
    "N":  (0.188, 0.314, 0.973), "O":  (1.000, 0.051, 0.051),
    "F":  (0.565, 0.878, 0.314), "Ne": (0.702, 0.890, 0.961),
    "Na": (0.671, 0.361, 0.949), "Mg": (0.541, 1.000, 0.000),
    "Al": (0.749, 0.651, 0.651), "Si": (0.941, 0.784, 0.627),
    "P":  (1.000, 0.502, 0.000), "S":  (1.000, 1.000, 0.188),
    "Cl": (0.122, 0.941, 0.122), "Ar": (0.502, 0.820, 0.890),
    "K":  (0.561, 0.251, 0.831), "Ca": (0.239, 1.000, 0.000),
    "Sc": (0.902, 0.902, 0.902), "Ti": (0.749, 0.761, 0.780),
    "V":  (0.651, 0.651, 0.671), "Cr": (0.541, 0.600, 0.780),
    "Mn": (0.612, 0.478, 0.780), "Fe": (0.878, 0.400, 0.200),
    "Co": (0.941, 0.565, 0.627), "Ni": (0.314, 0.816, 0.314),
    "Cu": (0.784, 0.502, 0.200), "Zn": (0.490, 0.502, 0.690),
    "Ga": (0.761, 0.561, 0.561), "Ge": (0.400, 0.561, 0.561),
    "As": (0.741, 0.502, 0.890), "Se": (1.000, 0.631, 0.000),
    "Br": (0.651, 0.161, 0.161), "Sr": (0.000, 1.000, 0.000),
    "Y":  (0.580, 1.000, 1.000), "Zr": (0.580, 0.878, 0.878),
    "Nb": (0.451, 0.761, 0.788), "Mo": (0.329, 0.710, 0.710),
    "Ru": (0.141, 0.561, 0.561), "Rh": (0.039, 0.490, 0.549),
    "Pd": (0.000, 0.412, 0.522), "Ag": (0.753, 0.753, 0.753),
    "Cd": (1.000, 0.851, 0.561), "In": (0.651, 0.459, 0.451),
    "Sn": (0.400, 0.502, 0.502), "Sb": (0.620, 0.388, 0.710),
    "Te": (0.831, 0.478, 0.000), "I":  (0.580, 0.000, 0.580),
    "Ba": (0.000, 0.788, 0.000), "La": (0.439, 0.831, 1.000),
    "Ce": (1.000, 1.000, 0.780), "W":  (0.129, 0.580, 0.839),
    "Re": (0.149, 0.490, 0.671), "Os": (0.149, 0.400, 0.588),
    "Ir": (0.090, 0.329, 0.529), "Pt": (0.816, 0.816, 0.878),
    "Au": (1.000, 0.820, 0.137), "Pb": (0.341, 0.349, 0.380),
    "Bi": (0.620, 0.310, 0.710),
}

# Fallback radius when Element.atomic_radius is None
DEFAULT_RADIUS = 1.2


def get_element_color(element):
    """Return RGB tuple for an element."""
    symbol = element.symbol if hasattr(element, "symbol") else str(element)
    return JMOL_COLORS.get(symbol, (0.5, 0.5, 0.5))


def get_element_radius(element):
    """Return atomic radius in Angstroms."""
    try:
        elem = Element(element) if isinstance(element, str) else element
        r = elem.atomic_radius
        return float(r) if r else DEFAULT_RADIUS
    except Exception:
        return DEFAULT_RADIUS


def plot_structure_3d(ax, structure, show_box=True, show_labels=True):
    """
    Plot a pymatgen Structure on a matplotlib 3D Axes.

    Args:
        ax: matplotlib Axes3D instance
        structure: pymatgen Structure or Slab
        show_box: draw the unit cell bounding box
        show_labels: show element labels on atoms
    """
    ax.clear()

    if structure is None or len(structure) == 0:
        ax.set_xlabel("x (\u00c5)")
        ax.set_ylabel("y (\u00c5)")
        ax.set_zlabel("z (\u00c5)")
        ax.text(0.5, 0.5, 0.5, "No structure", transform=ax.transAxes,
                ha="center", va="center", fontsize=12, color="gray")
        return

    # Collect atom data grouped by element for efficient plotting
    element_groups = {}
    for site in structure:
        symbol = site.specie.symbol if hasattr(site.specie, "symbol") else str(site.specie)
        if symbol not in element_groups:
            element_groups[symbol] = {
                "coords": [],
                "color": get_element_color(site.specie),
                "radius": get_element_radius(site.specie),
            }
        element_groups[symbol]["coords"].append(site.coords)

    # Plot atoms by element group
    for symbol, data in element_groups.items():
        coords = np.array(data["coords"])
        # Scale radius: 1.0 Ang -> scatter size ~200
        scatter_size = (data["radius"] / DEFAULT_RADIUS) ** 2 * 200
        ax.scatter(
            coords[:, 0], coords[:, 1], coords[:, 2],
            c=[data["color"]],
            s=scatter_size,
            alpha=0.9,
            edgecolors="black",
            linewidth=0.5,
            label=symbol,
            depthshade=True,
        )

    # Draw unit cell bounding box
    if show_box:
        _draw_lattice_box(ax, structure.lattice)

    # Axes labels
    ax.set_xlabel("x (\u00c5)")
    ax.set_ylabel("y (\u00c5)")
    ax.set_zlabel("z (\u00c5)")

    # Legend
    ax.legend(loc="upper left", fontsize=8, framealpha=0.7)

    # Equal aspect ratio approximation
    all_coords = np.array([site.coords for site in structure])
    _set_equal_aspect(ax, all_coords)


def _draw_lattice_box(ax, lattice):
    """Draw the 12 edges of the unit cell parallelepiped."""
    origin = np.array([0.0, 0.0, 0.0])
    a, b, c = lattice.matrix

    # 8 corners of the parallelepiped
    corners = [
        origin, a, b, c,
        a + b, a + c, b + c,
        a + b + c,
    ]

    # 12 edges connecting the corners
    edges = [
        (0, 1), (0, 2), (0, 3),
        (1, 4), (1, 5),
        (2, 4), (2, 6),
        (3, 5), (3, 6),
        (4, 7), (5, 7), (6, 7),
    ]

    for i, j in edges:
        pts = np.array([corners[i], corners[j]])
        ax.plot(pts[:, 0], pts[:, 1], pts[:, 2],
                color="gray", linewidth=0.8, alpha=0.5)


def _set_equal_aspect(ax, coords):
    """Set approximately equal aspect ratio for 3D axes."""
    if len(coords) == 0:
        return
    mins = coords.min(axis=0)
    maxs = coords.max(axis=0)
    ranges = maxs - mins
    max_range = ranges.max()
    if max_range < 1e-6:
        max_range = 1.0
    centers = (mins + maxs) / 2.0
    padding = max_range / 2.0 * 1.1
    ax.set_xlim(centers[0] - padding, centers[0] + padding)
    ax.set_ylim(centers[1] - padding, centers[1] + padding)
    ax.set_zlim(centers[2] - padding, centers[2] + padding)
