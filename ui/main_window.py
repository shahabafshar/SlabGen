import os
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget,
    QSpinBox, QMessageBox, QGroupBox, QCheckBox, QDoubleSpinBox, QComboBox,
    QFileDialog, QStatusBar, QFrame, QApplication,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtGui import QKeySequence, QShortcut

from pymatgen.core import Structure

try:
    from mp_api.client import MPRester
    HAS_MP_API = True
except ImportError:
    HAS_MP_API = False
from pymatgen.io.vasp.inputs import Poscar
from pymatgen.io.cif import CifWriter

from core.slab_generator import (
    oriented_slab_replication,
    extract_surface_regions,
    compare_structures,
)
from ui.viewer_widget import StructureViewer
from ui.screening_dialog import ScreeningDialog
from ui.dft_dialog import DFTInputDialog


# ── Background Workers ──

class SearchWorker(QThread):
    """Run MP API search in a background thread."""
    finished = Signal(list)   # list of docs
    error = Signal(str)

    def __init__(self, api_key, formula):
        super().__init__()
        self.api_key = api_key
        self.formula = formula

    def run(self):
        try:
            with MPRester(self.api_key) as mpr:
                docs = mpr.materials.search(formula=self.formula)
            self.finished.emit(docs if docs else [])
        except Exception as e:
            self.error.emit(str(e))


class SlabWorker(QThread):
    """Run slab generation in a background thread."""
    finished = Signal(list)   # list of Slab objects
    error = Signal(str)

    def __init__(self, structure, h, k, l, z_reps, min_vac,
                 center_slab, all_terminations, force_ortho):
        super().__init__()
        self.structure = structure
        self.h, self.k, self.l = h, k, l
        self.z_reps = z_reps
        self.min_vac = min_vac
        self.center_slab = center_slab
        self.all_terminations = all_terminations
        self.force_ortho = force_ortho

    def run(self):
        try:
            slabs = oriented_slab_replication(
                structure=self.structure,
                h=self.h, k=self.k, l=self.l,
                z_reps=self.z_reps,
                min_vac=self.min_vac,
                center_slab=self.center_slab,
                all_terminations=self.all_terminations,
                force_ortho=self.force_ortho,
            )
            self.finished.emit(slabs if slabs else [])
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SlabGen v1.0 — Surface Slab Generation Platform")
        self.setMinimumSize(1100, 750)  # UX #16

        # Read MP API key
        self.api_key = self._read_api_key("mp_api_key.txt")

        # Data holders
        self.structure_docs = []
        self.selected_doc_index = None
        self.generated_slabs = []
        self.local_structure = None
        self._search_worker = None
        self._slab_worker = None

        # Build UI
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # ── Status bar (UX #8) ──
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready — search Materials Project or upload a local structure file.")

        # ── 1) TOP SECTION: Search / OR / Upload ──
        top_layout = QHBoxLayout()

        left_col_group = QGroupBox("Search Materials Project")
        left_col_vlayout = QVBoxLayout()

        formula_layout = QHBoxLayout()
        self.formula_label = QLabel("Formula:")
        self.formula_input = QLineEdit()
        self.formula_input.setPlaceholderText("e.g. Mo2C, TiO2, Fe")
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_structures)
        formula_layout.addWidget(self.formula_label)
        formula_layout.addWidget(self.formula_input)
        formula_layout.addWidget(self.search_button)
        left_col_vlayout.addLayout(formula_layout)

        self.struct_table = QTableWidget()
        self.struct_table.setColumnCount(6)
        self.struct_table.setHorizontalHeaderLabels([
            "ID", "Formula", "Space Group", "Crystal System", "Atoms", "E_hull (eV)"
        ])
        self.struct_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.struct_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.struct_table.setSelectionMode(QTableWidget.SingleSelection)
        self.struct_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.struct_table.currentCellChanged.connect(
            lambda row, *_: self.on_doc_selected(row))
        left_col_vlayout.addWidget(self.struct_table)
        left_col_group.setLayout(left_col_vlayout)

        # UX #11: Replace empty QGroupBox with a plain vertical separator
        separator_widget = QWidget()
        separator_layout = QVBoxLayout()
        separator_layout.setContentsMargins(5, 0, 5, 0)
        separator_layout.addStretch(1)

        separator_line_top = QFrame()
        separator_line_top.setFrameShape(QFrame.VLine)
        separator_line_top.setFrameShadow(QFrame.Sunken)
        separator_layout.addWidget(separator_line_top)

        self.or_label = QLabel("OR")
        font = self.or_label.font()
        font.setPointSize(12)
        font.setBold(True)
        self.or_label.setFont(font)
        separator_layout.addWidget(self.or_label, alignment=Qt.AlignHCenter)

        separator_line_bot = QFrame()
        separator_line_bot.setFrameShape(QFrame.VLine)
        separator_line_bot.setFrameShadow(QFrame.Sunken)
        separator_layout.addWidget(separator_line_bot)

        separator_layout.addStretch(1)
        separator_widget.setLayout(separator_layout)

        # UX #12: Improved upload area
        right_col_group = QGroupBox("Local Upload")
        right_col_layout = QVBoxLayout()
        right_col_layout.addStretch(1)

        upload_hint = QLabel("Load a POSCAR, CONTCAR, or CIF file")
        upload_hint.setAlignment(Qt.AlignHCenter)
        upload_hint.setStyleSheet("color: #666; font-size: 10px;")
        right_col_layout.addWidget(upload_hint)

        self.upload_button = QPushButton("Browse Files...")
        self.upload_button.setMinimumHeight(40)
        self.upload_button.clicked.connect(self.upload_bulk_structure)
        right_col_layout.addWidget(self.upload_button)

        self.filename_line = QLineEdit()
        self.filename_line.setPlaceholderText("No file selected")
        self.filename_line.setReadOnly(True)
        right_col_layout.addWidget(self.filename_line)
        right_col_layout.addStretch(1)
        right_col_group.setLayout(right_col_layout)

        top_layout.addWidget(left_col_group, stretch=6)
        top_layout.addWidget(separator_widget, stretch=1)
        top_layout.addWidget(right_col_group, stretch=2)
        main_layout.addLayout(top_layout)

        # ── 2) BASIC SLAB OPTIONS ──
        slab_options_group = QGroupBox("Basic Slab Options")
        slab_layout = QHBoxLayout()

        slab_layout.addWidget(QLabel("h:"))
        self.h_spin = QSpinBox()
        self.h_spin.setRange(-10, 10)
        self.h_spin.setValue(0)
        slab_layout.addWidget(self.h_spin)

        slab_layout.addWidget(QLabel("k:"))
        self.k_spin = QSpinBox()
        self.k_spin.setRange(-10, 10)
        self.k_spin.setValue(0)
        slab_layout.addWidget(self.k_spin)

        slab_layout.addWidget(QLabel("l:"))
        self.l_spin = QSpinBox()
        self.l_spin.setRange(-10, 10)
        self.l_spin.setValue(1)
        slab_layout.addWidget(self.l_spin)

        slab_layout.addWidget(QLabel("Z Reps:"))
        self.zreps_spin = QSpinBox()
        self.zreps_spin.setRange(1, 50)
        self.zreps_spin.setValue(1)
        slab_layout.addWidget(self.zreps_spin)

        # UX #18: In-plane supercell
        slab_layout.addWidget(QLabel("In-plane:"))
        self.supercell_a_spin = QSpinBox()
        self.supercell_a_spin.setRange(1, 10)
        self.supercell_a_spin.setValue(1)
        self.supercell_a_spin.setToolTip("Supercell repeat along a-axis")
        slab_layout.addWidget(self.supercell_a_spin)
        slab_layout.addWidget(QLabel("\u00d7"))
        self.supercell_b_spin = QSpinBox()
        self.supercell_b_spin.setRange(1, 10)
        self.supercell_b_spin.setValue(1)
        self.supercell_b_spin.setToolTip("Supercell repeat along b-axis")
        slab_layout.addWidget(self.supercell_b_spin)

        slab_layout.addWidget(QLabel("Vacuum (\u00c5):"))
        self.vacuum_spin = QDoubleSpinBox()
        self.vacuum_spin.setRange(0.0, 100.0)
        self.vacuum_spin.setValue(10.0)
        self.vacuum_spin.setSingleStep(0.5)
        slab_layout.addWidget(self.vacuum_spin)

        slab_layout.addWidget(QLabel("Vac Placement:"))
        self.vac_placement_combo = QComboBox()
        self.vac_placement_combo.addItems(["top-only", "centered"])
        slab_layout.addWidget(self.vac_placement_combo)

        self.ortho_check = QCheckBox("Orthogonal c-axis?")
        slab_layout.addWidget(self.ortho_check)

        slab_options_group.setLayout(slab_layout)
        main_layout.addWidget(slab_options_group)

        # ── 3) ADVANCED OPTIONS ──
        adv_options_group = QGroupBox("Advanced Options")
        adv_layout = QHBoxLayout()

        self.all_terminations_check = QCheckBox("All Terminations?")
        adv_layout.addWidget(self.all_terminations_check)

        self.comparison_check = QCheckBox("Do Comparison? (Slow)")
        self.comparison_check.stateChanged.connect(self._toggle_comparison_options)
        adv_layout.addWidget(self.comparison_check)

        self.generate_cleaves_check = QCheckBox("Separate top/bot files?")
        self.generate_cleaves_check.setEnabled(False)
        adv_layout.addWidget(self.generate_cleaves_check)

        adv_layout.addWidget(QLabel("Depth (\u00c5):"))
        self.compare_depth_spin = QDoubleSpinBox()
        self.compare_depth_spin.setRange(0.0, 100.0)
        self.compare_depth_spin.setValue(5.0)
        self.compare_depth_spin.setEnabled(False)
        adv_layout.addWidget(self.compare_depth_spin)

        self.generate_slabs_button = QPushButton("Generate Slabs")
        self.generate_slabs_button.clicked.connect(self.generate_slabs)
        adv_layout.addWidget(self.generate_slabs_button)

        self.screen_button = QPushButton("Screen All Surfaces")
        self.screen_button.clicked.connect(self._open_screening_dialog)
        adv_layout.addWidget(self.screen_button)

        adv_options_group.setLayout(adv_layout)
        main_layout.addWidget(adv_options_group)

        # ── 4) SLABS LIST + INFO PANEL + 3D VIEWER ──
        middle_section = QHBoxLayout()

        # Left: slab list + info panel stacked
        left_panel = QVBoxLayout()

        slabs_group = QGroupBox("Generated Slabs")
        slabs_vlayout = QVBoxLayout()
        self.slabs_table = QTableWidget()
        self.slabs_table.setColumnCount(5)
        self.slabs_table.setHorizontalHeaderLabels([
            "Formula", "Shift", "Atoms", "Area (\u00c5\u00b2)", "Symmetric"
        ])
        self.slabs_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.slabs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.slabs_table.setSelectionMode(QTableWidget.SingleSelection)
        self.slabs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.slabs_table.currentCellChanged.connect(
            lambda row, *_: self._on_slab_selected(row))
        slabs_vlayout.addWidget(self.slabs_table)
        slabs_group.setLayout(slabs_vlayout)
        left_panel.addWidget(slabs_group, stretch=3)

        # UX #7: Slab properties info panel
        info_group = QGroupBox("Slab Properties")
        info_layout = QVBoxLayout()
        self.slab_info_text = QTextEdit()
        self.slab_info_text.setReadOnly(True)
        self.slab_info_text.setMaximumHeight(140)
        self.slab_info_text.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        self.slab_info_text.setPlaceholderText("Select a slab to view its properties")
        info_layout.addWidget(self.slab_info_text)
        info_group.setLayout(info_layout)
        left_panel.addWidget(info_group, stretch=1)

        middle_section.addLayout(left_panel, stretch=4)

        viewer_group = QGroupBox("3D Structure Viewer")
        viewer_vlayout = QVBoxLayout()
        self.structure_viewer = StructureViewer()
        viewer_vlayout.addWidget(self.structure_viewer)
        viewer_group.setLayout(viewer_vlayout)
        middle_section.addWidget(viewer_group, stretch=5)

        main_layout.addLayout(middle_section)

        # ── 5) EXPORT BUTTONS ──
        export_layout = QHBoxLayout()
        self.export_button = QPushButton("Export Selected Slab")
        self.export_button.clicked.connect(self.export_selected_slab)
        export_layout.addWidget(self.export_button)

        # Feature #22: Export all terminations
        self.export_all_button = QPushButton("Export All Slabs")
        self.export_all_button.clicked.connect(self._export_all_slabs)
        export_layout.addWidget(self.export_all_button)

        self.dft_button = QPushButton("Prepare DFT Inputs")
        self.dft_button.clicked.connect(self._open_dft_dialog)
        export_layout.addWidget(self.dft_button)

        main_layout.addLayout(export_layout)

        # ── Keyboard Shortcuts (UX #10) ──
        QShortcut(QKeySequence("Return"), self.formula_input, self.search_structures)
        QShortcut(QKeySequence("Ctrl+G"), self, self.generate_slabs)
        QShortcut(QKeySequence("Ctrl+E"), self, self.export_selected_slab)
        QShortcut(QKeySequence("Ctrl+D"), self, self._open_dft_dialog)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, self._open_screening_dialog)
        QShortcut(QKeySequence("Ctrl+O"), self, self.upload_bulk_structure)

    # ── UI Helpers ──

    def _on_slab_selected(self, row):
        """Update 3D viewer and info panel when user selects a slab."""
        if 0 <= row < len(self.generated_slabs):
            slab = self.generated_slabs[row]
            self.structure_viewer.update_structure(slab)
            self._update_slab_info(slab)
        else:
            self.slab_info_text.clear()

    def _update_slab_info(self, slab):
        """Populate the slab properties info panel (UX #7 + Feature #20)."""
        all_z = [site.coords[2] for site in slab]
        z_min, z_max = min(all_z), max(all_z)
        thickness = z_max - z_min

        try:
            is_sym = slab.is_symmetric()
            sym_str = "Yes" if is_sym else "No"
        except Exception:
            sym_str = "N/A"

        a, b, c = slab.lattice.abc
        alpha, beta, gamma = slab.lattice.angles
        shift_val = getattr(slab, "shift", "N/A")

        info = (
            f"Formula:        {slab.composition.reduced_formula}\n"
            f"Num atoms:      {len(slab)}\n"
            f"Surface area:   {slab.surface_area:.2f} \u00c5\u00b2\n"
            f"Slab thickness: {thickness:.2f} \u00c5\n"
            f"Symmetric:      {sym_str}\n"
            f"Shift:          {shift_val}\n"
            f"Lattice:        a={a:.3f}  b={b:.3f}  c={c:.3f} \u00c5\n"
            f"Angles:         \u03b1={alpha:.1f}\u00b0  \u03b2={beta:.1f}\u00b0  \u03b3={gamma:.1f}\u00b0"
        )
        self.slab_info_text.setPlainText(info)

    def _toggle_comparison_options(self):
        do_compare = self.comparison_check.isChecked()
        self.compare_depth_spin.setEnabled(do_compare)
        self.generate_cleaves_check.setEnabled(do_compare)

    def _read_api_key(self, path):
        if not os.path.exists(path):
            return ""
        with open(path, "r") as f:
            return f.read().strip()

    def _get_chosen_structure(self):
        """Return the currently selected bulk structure, or None."""
        if self.local_structure is not None:
            return self.local_structure.copy()
        if (self.selected_doc_index is not None and
                0 <= self.selected_doc_index < len(self.structure_docs)):
            doc = self.structure_docs[self.selected_doc_index]
            if doc.structure:
                return doc.structure.copy()
        return None

    def _get_material_id(self):
        """Return material ID string for filename."""
        if self.local_structure is not None:
            return "LOCAL"
        if (self.selected_doc_index is not None and
                0 <= self.selected_doc_index < len(self.structure_docs)):
            doc = self.structure_docs[self.selected_doc_index]
            return str(doc.material_id) if doc.material_id else "UNKNOWN"
        return "UNKNOWN"

    def _set_controls_enabled(self, enabled):
        """Enable/disable generation controls during background operations."""
        self.generate_slabs_button.setEnabled(enabled)
        self.search_button.setEnabled(enabled)
        self.screen_button.setEnabled(enabled)
        self.export_button.setEnabled(enabled)
        self.export_all_button.setEnabled(enabled)
        self.dft_button.setEnabled(enabled)

    # ── Screening (UX #9: pass main window params) ──

    def _open_screening_dialog(self):
        """Open the batch surface screening dialog."""
        structure = self._get_chosen_structure()
        if structure is None:
            QMessageBox.warning(self, "Error",
                                "No bulk structure. Select from MP or upload a POSCAR first.")
            return
        # UX #9: Pass current main window parameters to screening dialog
        params = {
            "z_reps": self.zreps_spin.value(),
            "vacuum": self.vacuum_spin.value(),
            "placement": self.vac_placement_combo.currentText(),
            "ortho": self.ortho_check.isChecked(),
        }
        dialog = ScreeningDialog(structure, parent=self, initial_params=params)
        dialog.load_surface.connect(self._load_from_screening)
        dialog.exec()

    def _load_from_screening(self, slab, miller):
        """Load a surface from the screening dialog into the main window."""
        h, k, l = miller
        self.h_spin.setValue(h)
        self.k_spin.setValue(k)
        self.l_spin.setValue(l)
        self.generated_slabs = [slab]
        self.slabs_table.setRowCount(1)

        shift_val = getattr(slab, "shift", 0.0)
        formula = slab.composition.reduced_formula

        try:
            sym_str = "Yes" if slab.is_symmetric() else "No"
        except Exception:
            sym_str = "N/A"

        self.slabs_table.setItem(0, 0, QTableWidgetItem(formula))
        self.slabs_table.setItem(0, 1, QTableWidgetItem(f"{float(shift_val):.4f}"))
        self.slabs_table.setItem(0, 2, QTableWidgetItem(str(len(slab))))
        self.slabs_table.setItem(0, 3, QTableWidgetItem(f"{float(slab.surface_area):.2f}"))
        self.slabs_table.setItem(0, 4, QTableWidgetItem(sym_str))

        self.slabs_table.setCurrentCell(0, 0)
        self.status_bar.showMessage(
            f"Loaded ({h},{k},{l}) surface from screening — shift={shift_val:.2f}")

    # ── Search & Upload (UX #6: background thread, UX #13: richer info) ──

    def search_structures(self):
        formula = self.formula_input.text().strip()
        if not formula:
            QMessageBox.warning(self, "Error", "Please enter a formula or upload a bulk file.")
            return
        if not HAS_MP_API:
            QMessageBox.warning(self, "Missing Dependency",
                                "The 'mp-api' package is not installed.\n"
                                "Install it with: pip install mp-api\n\n"
                                "You can still use local file upload.")
            return
        if not self.api_key:
            QMessageBox.warning(self, "Warning",
                                "No API key found. Provide mp_api_key.txt or use local upload.")
            return

        self.struct_table.setRowCount(0)
        self.structure_docs.clear()
        self._set_controls_enabled(False)
        self.status_bar.showMessage(f"Searching Materials Project for '{formula}'...")
        QApplication.processEvents()

        self._search_worker = SearchWorker(self.api_key, formula)
        self._search_worker.finished.connect(self._on_search_finished)
        self._search_worker.error.connect(self._on_search_error)
        self._search_worker.start()

    def _on_search_finished(self, docs):
        self._set_controls_enabled(True)
        if not docs:
            formula = self.formula_input.text().strip()
            self.status_bar.showMessage(f"No results for '{formula}'.")
            QMessageBox.information(self, "No Results",
                                    f"No structures found for '{formula}'.")
            return

        self.structure_docs = docs
        self.struct_table.setRowCount(len(docs))
        for row, doc in enumerate(docs):
            mat_id = str(doc.material_id) if doc.material_id else "N/A"
            pretty_formula = str(doc.formula_pretty) if doc.formula_pretty else "N/A"
            sg_symbol = str(doc.symmetry.symbol) if doc.symmetry else "N/A"
            crystal_sys = str(doc.symmetry.crystal_system) if doc.symmetry else "N/A"
            n_atoms = len(doc.structure) if doc.structure else 0
            e_hull = getattr(doc, "energy_above_hull", None)

            self.struct_table.setItem(row, 0, QTableWidgetItem(mat_id))
            self.struct_table.setItem(row, 1, QTableWidgetItem(pretty_formula))
            self.struct_table.setItem(row, 2, QTableWidgetItem(sg_symbol))
            self.struct_table.setItem(row, 3, QTableWidgetItem(crystal_sys))

            atoms_item = QTableWidgetItem()
            atoms_item.setData(Qt.DisplayRole, n_atoms)
            self.struct_table.setItem(row, 4, atoms_item)

            ehull_item = QTableWidgetItem()
            if e_hull is not None:
                ehull_item.setData(Qt.DisplayRole, round(e_hull, 4))
            else:
                ehull_item.setText("N/A")
            self.struct_table.setItem(row, 5, ehull_item)

        self.local_structure = None
        self.selected_doc_index = None
        self.status_bar.showMessage(
            f"Found {len(docs)} structures for '{self.formula_input.text().strip()}'.")

    def _on_search_error(self, error_msg):
        self._set_controls_enabled(True)
        self.status_bar.showMessage("Search failed.")
        QMessageBox.critical(self, "Search Error", f"Error:\n{error_msg}")

    def on_doc_selected(self, row):
        self.selected_doc_index = row
        if (self.selected_doc_index is not None and
                0 <= self.selected_doc_index < len(self.structure_docs)):
            doc = self.structure_docs[self.selected_doc_index]
            if doc.structure:
                self.structure_viewer.update_structure(doc.structure)
                mat_id = doc.material_id
                self.status_bar.showMessage(
                    f"Selected {mat_id} — {doc.formula_pretty} "
                    f"({len(doc.structure)} atoms)")

    def upload_bulk_structure(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select a bulk structure file",
            "",
            "Structure files (*.vasp *.cif *.POSCAR *.CONTCAR);;CIF files (*.cif);;VASP files (*.vasp *.POSCAR *.CONTCAR);;All Files (*)"
        )
        if file_path:
            try:
                struct = Structure.from_file(file_path)
                self.local_structure = struct
                self.filename_line.setText(os.path.basename(file_path))
                self.struct_table.setRowCount(0)
                self.structure_docs.clear()
                self.selected_doc_index = None
                self.structure_viewer.update_structure(struct)
                self.status_bar.showMessage(
                    f"Loaded {os.path.basename(file_path)} — "
                    f"{struct.composition.reduced_formula} ({len(struct)} atoms)")
            except Exception as ex:
                QMessageBox.critical(self, "Error",
                                     f"Failed to read structure:\n{str(ex)}")

    # ── Generate Slabs (UX #6: background thread) ──

    def generate_slabs(self):
        chosen_structure = self._get_chosen_structure()
        if chosen_structure is None:
            QMessageBox.warning(self, "Error",
                                "No bulk structure. Select from MP or upload a POSCAR.")
            return

        h = self.h_spin.value()
        k = self.k_spin.value()
        l_val = self.l_spin.value()

        if h == 0 and k == 0 and l_val == 0:
            QMessageBox.warning(self, "Error",
                                "Miller indices (0,0,0) are invalid. At least one must be non-zero.")
            return

        z_reps = self.zreps_spin.value()
        vac_thick = self.vacuum_spin.value()
        center_slab = (self.vac_placement_combo.currentText() == "centered")
        force_ortho = self.ortho_check.isChecked()
        all_terms = self.all_terminations_check.isChecked()

        self.slabs_table.setRowCount(0)
        self.generated_slabs.clear()
        self.slab_info_text.clear()
        self._set_controls_enabled(False)
        self.status_bar.showMessage(
            f"Generating ({h},{k},{l_val}) slabs...")

        # Store comparison settings for use in callback
        self._pending_compare = self.comparison_check.isChecked()
        self._pending_compare_depth = self.compare_depth_spin.value()
        self._pending_supercell = (self.supercell_a_spin.value(),
                                   self.supercell_b_spin.value())

        self._slab_worker = SlabWorker(
            chosen_structure, h, k, l_val, z_reps, vac_thick,
            center_slab, all_terms, force_ortho)
        self._slab_worker.finished.connect(self._on_slabs_generated)
        self._slab_worker.error.connect(self._on_slab_error)
        self._slab_worker.start()

    def _on_slabs_generated(self, final_slabs):
        self._set_controls_enabled(True)

        if not final_slabs:
            self.status_bar.showMessage("No slabs generated.")
            QMessageBox.information(self, "No Slab Generated",
                                    "No slabs were created with these parameters.")
            return

        # Apply in-plane supercell if requested (Feature #18)
        sa, sb = self._pending_supercell
        if sa > 1 or sb > 1:
            expanded = []
            for slab in final_slabs:
                slab.make_supercell([sa, sb, 1])
                expanded.append(slab)
            final_slabs = expanded

        do_compare = self._pending_compare
        compare_depth = self._pending_compare_depth

        self.generated_slabs = final_slabs
        self.slabs_table.setRowCount(len(final_slabs))

        for i, slab in enumerate(final_slabs):
            shift_val = getattr(slab, "shift", float(i))
            formula = slab.composition.reduced_formula
            n_atoms = len(slab)
            area = slab.surface_area

            try:
                is_sym = slab.is_symmetric()
                sym_str = "Yes" if is_sym else "No"
            except Exception:
                sym_str = "N/A"

            self.slabs_table.setItem(i, 0, QTableWidgetItem(formula))
            self.slabs_table.setItem(i, 1, QTableWidgetItem(f"{float(shift_val):.4f}"))
            self.slabs_table.setItem(i, 2, QTableWidgetItem(str(int(n_atoms))))
            self.slabs_table.setItem(i, 3, QTableWidgetItem(f"{float(area):.2f}"))
            self.slabs_table.setItem(i, 4, QTableWidgetItem(sym_str))

        if self.generated_slabs:
            self.slabs_table.setCurrentCell(0, 0)

        h = self.h_spin.value()
        k = self.k_spin.value()
        l_val = self.l_spin.value()
        self.status_bar.showMessage(
            f"Generated {len(final_slabs)} slab(s) for ({h},{k},{l_val}).")

    def _on_slab_error(self, error_msg):
        self._set_controls_enabled(True)
        self.status_bar.showMessage("Slab generation failed.")
        QMessageBox.critical(self, "Error", f"Slab generation error:\n{error_msg}")

    # ── DFT Inputs ──

    def _open_dft_dialog(self):
        """Open the DFT input generation dialog for the selected slab."""
        slab_index = self.slabs_table.currentRow()
        if slab_index < 0 or slab_index >= len(self.generated_slabs):
            QMessageBox.warning(self, "Error", "No slab selected.")
            return
        slab = self.generated_slabs[slab_index]
        mat_id = self._get_material_id()
        h, k, l_val = self.h_spin.value(), self.k_spin.value(), self.l_spin.value()
        suggested = f"{mat_id}_{h}{k}{l_val}_dft"
        dialog = DFTInputDialog(slab, suggested_dir_name=suggested, parent=self)
        dialog.exec()

    # ── Export ──

    def export_selected_slab(self):
        slab_index = self.slabs_table.currentRow()
        if slab_index < 0 or slab_index >= len(self.generated_slabs):
            QMessageBox.warning(self, "Error", "No slab selected.")
            return
        try:
            slab = self.generated_slabs[slab_index]
            save_path = self._save_slab_dialog(slab, slab_index)
            if not save_path:
                return

            do_compare = self.comparison_check.isChecked()
            do_cleaves = self.generate_cleaves_check.isChecked()

            if do_compare and do_cleaves:
                compare_depth = self.compare_depth_spin.value()
                top_struct, bottom_rot = extract_surface_regions(slab, compare_depth)

                base_no_ext = os.path.splitext(save_path)[0]
                top_path = f"{base_no_ext}_top.vasp"
                bottom_path = f"{base_no_ext}_bottom_rot.vasp"

                if top_struct and len(top_struct) > 0:
                    Poscar(top_struct).write_file(top_path)
                if bottom_rot and len(bottom_rot) > 0:
                    Poscar(bottom_rot).write_file(bottom_path)

                msg = (f"Exported slab => {save_path}\n"
                       f"Top => {top_path}\nBottom(rot) => {bottom_path}")
            else:
                msg = f"Exported slab => {save_path}"

            self.status_bar.showMessage(f"Exported slab to {os.path.basename(save_path)}")
            QMessageBox.information(self, "Success", msg)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export error:\n{str(e)}")

    def _save_slab_dialog(self, slab, slab_index):
        """Show save dialog and write slab file. Returns saved path or None."""
        mat_id = self._get_material_id()
        h = self.h_spin.value()
        k = self.k_spin.value()
        l_val = self.l_spin.value()
        z_reps = self.zreps_spin.value()
        vac_thick = self.vacuum_spin.value()
        ortho_flag = "ortho" if self.ortho_check.isChecked() else "nonortho"
        vac_mode = self.vac_placement_combo.currentText()
        shift_val = getattr(slab, "shift", slab_index)

        main_name = (
            f"POSCAR_{mat_id}_{h}-{k}-{l_val}_z{z_reps}_"
            f"vac{vac_thick}_{vac_mode}{ortho_flag}_shift{shift_val}"
        ).replace(".", "-") + ".vasp"

        save_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Save Slab", main_name,
            "VASP files (*.vasp *.POSCAR);;CIF files (*.cif);;All Files (*)"
        )
        if not save_path:
            return None

        if save_path.endswith(".cif") or "CIF" in selected_filter:
            CifWriter(slab).write_file(save_path)
        else:
            Poscar(slab).write_file(save_path)

        return save_path

    def _export_all_slabs(self):
        """Export all generated slabs to a directory (Feature #22)."""
        if not self.generated_slabs:
            QMessageBox.warning(self, "Error", "No slabs to export.")
            return

        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory for All Slabs")
        if not output_dir:
            return

        mat_id = self._get_material_id()
        h = self.h_spin.value()
        k = self.k_spin.value()
        l_val = self.l_spin.value()
        z_reps = self.zreps_spin.value()
        vac_thick = self.vacuum_spin.value()
        ortho_flag = "ortho" if self.ortho_check.isChecked() else "nonortho"
        vac_mode = self.vac_placement_combo.currentText()

        exported = []
        for i, slab in enumerate(self.generated_slabs):
            shift_val = getattr(slab, "shift", i)
            fname = (
                f"POSCAR_{mat_id}_{h}-{k}-{l_val}_z{z_reps}_"
                f"vac{vac_thick}_{vac_mode}{ortho_flag}_shift{shift_val}"
            ).replace(".", "-") + ".vasp"
            fpath = os.path.join(output_dir, fname)
            Poscar(slab).write_file(fpath)
            exported.append(fname)

        self.status_bar.showMessage(
            f"Exported {len(exported)} slabs to {output_dir}")
        QMessageBox.information(
            self, "Export Complete",
            f"Exported {len(exported)} slabs to:\n{output_dir}\n\n"
            + "\n".join(f"  {f}" for f in exported))
