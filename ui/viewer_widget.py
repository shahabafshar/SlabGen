from PyQt5.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from core.visualization import plot_structure_3d


class StructureViewer(QWidget):
    """Embeddable 3D structure viewer using matplotlib."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.fig = Figure(figsize=(5, 5), dpi=100)
        self.fig.patch.set_facecolor("white")
        self.ax = self.fig.add_subplot(111, projection="3d")
        self.ax.set_facecolor("white")
        # Make pane faces near-white for contrast with Qt gray panels
        self.ax.xaxis.pane.fill = True
        self.ax.yaxis.pane.fill = True
        self.ax.zaxis.pane.fill = True
        self.ax.xaxis.pane.set_facecolor((0.95, 0.95, 0.98, 1.0))
        self.ax.yaxis.pane.set_facecolor((0.92, 0.92, 0.96, 1.0))
        self.ax.zaxis.pane.set_facecolor((0.96, 0.96, 0.99, 1.0))

        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        self._current_structure = None

        # Show empty state
        self.ax.set_xlabel("x (\u00c5)")
        self.ax.set_ylabel("y (\u00c5)")
        self.ax.set_zlabel("z (\u00c5)")
        self.ax.text2D(0.5, 0.5, "No structure loaded",
                       transform=self.ax.transAxes,
                       ha="center", va="center", fontsize=11, color="gray")
        self.canvas.draw()

    def update_structure(self, structure):
        """Update the 3D view with a new structure."""
        self._current_structure = structure
        plot_structure_3d(self.ax, structure)
        self.fig.tight_layout()
        self.canvas.draw()

    def clear(self):
        """Clear the viewer."""
        self._current_structure = None
        self.ax.clear()
        self.ax.set_xlabel("x (\u00c5)")
        self.ax.set_ylabel("y (\u00c5)")
        self.ax.set_zlabel("z (\u00c5)")
        self.ax.text2D(0.5, 0.5, "No structure loaded",
                       transform=self.ax.transAxes,
                       ha="center", va="center", fontsize=11, color="gray")
        self.canvas.draw()
