import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget,
    QSpinBox, QMessageBox, QGroupBox, QCheckBox, QDoubleSpinBox, QComboBox,
    QFileDialog
)

from mp_api.client import MPRester
from pymatgen.core import Structure
from pymatgen.io.vasp.inputs import Poscar

from core.slab_generator import (
    oriented_slab_replication,
    extract_surface_regions,
    compare_structures,
)
from ui.viewer_widget import StructureViewer
from ui.screening_dialog import ScreeningDialog
from ui.dft_dialog import DFTInputDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SlabGen v1.0 — Surface Slab Generation Platform")

        # Read MP API key
        self.api_key = self._read_api_key("mp_api_key.txt")

        # Data holders
        self.structure_docs = []
        self.selected_doc_index = None
        self.generated_slabs = []
        self.local_structure = None

        # Build UI
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # ── 1) TOP SECTION: Search / OR / Upload ──
        top_layout = QHBoxLayout()

        left_col_group = QGroupBox("Search Materials Project")
        left_col_vlayout = QVBoxLayout()

        formula_layout = QHBoxLayout()
        self.formula_label = QLabel("Formula:")
        self.formula_input = QLineEdit()
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_structures)
        formula_layout.addWidget(self.formula_label)
        formula_layout.addWidget(self.formula_input)
        formula_layout.addWidget(self.search_button)
        left_col_vlayout.addLayout(formula_layout)

        self.struct_list_widget = QListWidget()
        self.struct_list_widget.itemClicked.connect(self.on_doc_selected)
        left_col_vlayout.addWidget(self.struct_list_widget)
        left_col_group.setLayout(left_col_vlayout)

        middle_col_group = QGroupBox("")
        middle_col_layout = QVBoxLayout()
        middle_col_layout.addStretch(1)
        self.or_label = QLabel("OR")
        font = self.or_label.font()
        font.setPointSize(14)
        font.setBold(True)
        self.or_label.setFont(font)
        middle_col_layout.addWidget(self.or_label, alignment=Qt.AlignHCenter)
        middle_col_layout.addStretch(1)
        middle_col_group.setLayout(middle_col_layout)

        right_col_group = QGroupBox("Local Upload")
        right_col_layout = QVBoxLayout()
        right_col_layout.addStretch(1)
        self.upload_button = QPushButton("Upload")
        self.upload_button.setFixedSize(60, 60)
        self.upload_button.clicked.connect(self.upload_bulk_structure)
        right_col_layout.addWidget(self.upload_button, alignment=Qt.AlignHCenter)

        self.filename_line = QLineEdit()
        self.filename_line.setPlaceholderText("No file selected")
        self.filename_line.setReadOnly(True)
        right_col_layout.addWidget(self.filename_line, alignment=Qt.AlignHCenter)
        right_col_layout.addStretch(1)
        right_col_group.setLayout(right_col_layout)

        top_layout.addWidget(left_col_group, stretch=6)
        top_layout.addWidget(middle_col_group, stretch=1)
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

        # ── 4) SLABS LIST + 3D VIEWER (side by side) ──
        middle_section = QHBoxLayout()

        slabs_group = QGroupBox("Generated Slabs")
        slabs_vlayout = QVBoxLayout()
        self.slabs_list_widget = QListWidget()
        self.slabs_list_widget.currentRowChanged.connect(self._on_slab_selected)
        slabs_vlayout.addWidget(self.slabs_list_widget)
        slabs_group.setLayout(slabs_vlayout)
        middle_section.addWidget(slabs_group, stretch=4)

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

        self.dft_button = QPushButton("Prepare DFT Inputs")
        self.dft_button.clicked.connect(self._open_dft_dialog)
        export_layout.addWidget(self.dft_button)

        main_layout.addLayout(export_layout)

    # ── UI Helpers ──

    def _on_slab_selected(self, row):
        """Update 3D viewer when user selects a slab from the list."""
        if 0 <= row < len(self.generated_slabs):
            self.structure_viewer.update_structure(self.generated_slabs[row])

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

    # ── Screening ──

    def _open_screening_dialog(self):
        """Open the batch surface screening dialog."""
        structure = self._get_chosen_structure()
        if structure is None:
            QMessageBox.warning(self, "Error",
                                "No bulk structure. Select from MP or upload a POSCAR first.")
            return
        dialog = ScreeningDialog(structure, parent=self)
        dialog.load_surface.connect(self._load_from_screening)
        dialog.exec_()

    def _load_from_screening(self, slab, miller):
        """Load a surface from the screening dialog into the main window."""
        h, k, l = miller
        self.h_spin.setValue(h)
        self.k_spin.setValue(k)
        self.l_spin.setValue(l)
        self.generated_slabs = [slab]
        self.slabs_list_widget.clear()
        shift_val = getattr(slab, "shift", 0.0)
        item_str = (f"Slab 0: {slab.composition.reduced_formula}, "
                    f"shift={shift_val:.2f}")
        self.slabs_list_widget.addItem(item_str)
        self.slabs_list_widget.setCurrentRow(0)

    # ── Search & Upload ──

    def search_structures(self):
        formula = self.formula_input.text().strip()
        if not formula:
            QMessageBox.warning(self, "Error", "Please enter a formula or upload a bulk file.")
            return
        if not self.api_key:
            QMessageBox.warning(self, "Warning",
                                "No API key found. Provide mp_api_key.txt or use local upload.")
            return
        try:
            self.struct_list_widget.clear()
            self.structure_docs.clear()
            with MPRester(self.api_key) as mpr:
                docs = mpr.materials.search(formula=formula)
            if not docs:
                QMessageBox.information(self, "No Results",
                                        f"No structures found for '{formula}'.")
                return
            self.structure_docs = docs
            for doc in docs:
                mat_id = doc.material_id
                pretty_formula = doc.formula_pretty
                sg_symbol = doc.symmetry.symbol if doc.symmetry else "N/A"
                item_str = f"{mat_id} | {pretty_formula} | {sg_symbol}"
                self.struct_list_widget.addItem(item_str)

            self.local_structure = None
            self.selected_doc_index = None

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error:\n{str(e)}")

    def on_doc_selected(self, item):
        self.selected_doc_index = self.struct_list_widget.currentRow()

    def upload_bulk_structure(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select a bulk structure file (POSCAR/CONTCAR)",
            "",
            "VASP files (*.POSCAR *.CONTCAR *.vasp);;All Files (*)"
        )
        if file_path:
            try:
                struct = Structure.from_file(file_path)
                self.local_structure = struct
                self.filename_line.setText(os.path.basename(file_path))
                self.struct_list_widget.clear()
                self.structure_docs.clear()
                self.selected_doc_index = None
                self.structure_viewer.update_structure(struct)
                QMessageBox.information(self, "Success",
                    f"Local bulk structure loaded from:\n{file_path}\n({len(struct.sites)} atoms).")
            except Exception as ex:
                QMessageBox.critical(self, "Error",
                                     f"Failed to read structure:\n{str(ex)}")

    # ── Generate Slabs ──

    def generate_slabs(self):
        chosen_structure = self._get_chosen_structure()
        if chosen_structure is None:
            QMessageBox.warning(self, "Error",
                                "No bulk structure. Select from MP or upload a POSCAR.")
            return

        h = self.h_spin.value()
        k = self.k_spin.value()
        l = self.l_spin.value()

        if h == 0 and k == 0 and l == 0:
            QMessageBox.warning(self, "Error",
                                "Miller indices (0,0,0) are invalid. At least one must be non-zero.")
            return

        z_reps = self.zreps_spin.value()
        vac_thick = self.vacuum_spin.value()
        center_slab = (self.vac_placement_combo.currentText() == "centered")
        force_ortho = self.ortho_check.isChecked()
        all_terms = self.all_terminations_check.isChecked()

        do_compare = self.comparison_check.isChecked()
        compare_depth = self.compare_depth_spin.value()

        self.slabs_list_widget.clear()
        self.generated_slabs.clear()

        try:
            final_slabs = oriented_slab_replication(
                structure=chosen_structure,
                h=h, k=k, l=l,
                z_reps=z_reps,
                min_vac=vac_thick,
                center_slab=center_slab,
                all_terminations=all_terms,
                force_ortho=force_ortho
            )

            if not final_slabs:
                QMessageBox.information(self, "No Slab Generated",
                                        "No slabs were created with these parameters.")
                return

            self.generated_slabs = final_slabs

            for i, slab in enumerate(final_slabs):
                shift_val = getattr(slab, "shift", float(i))
                label_str = ""

                if do_compare:
                    top_struct, bottom_rot = extract_surface_regions(slab, compare_depth)
                    match_bool, rmsd_val = compare_structures(top_struct, bottom_rot)
                    if match_bool:
                        label_str = f"(match, RMSD={rmsd_val:.2f} \u00c5)"
                    else:
                        label_str = "(no match)"

                item_str = (f"Slab {i}: {slab.composition.reduced_formula}, "
                            f"shift={shift_val:.2f} {label_str}")
                self.slabs_list_widget.addItem(item_str)

            # Auto-select first slab and show in viewer
            if self.generated_slabs:
                self.slabs_list_widget.setCurrentRow(0)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Slab generation error:\n{str(e)}")

    # ── DFT Inputs ──

    def _open_dft_dialog(self):
        """Open the DFT input generation dialog for the selected slab."""
        slab_index = self.slabs_list_widget.currentRow()
        if slab_index < 0 or slab_index >= len(self.generated_slabs):
            QMessageBox.warning(self, "Error", "No slab selected.")
            return
        slab = self.generated_slabs[slab_index]
        mat_id = self._get_material_id()
        h, k, l = self.h_spin.value(), self.k_spin.value(), self.l_spin.value()
        suggested = f"{mat_id}_{h}{k}{l}_dft"
        dialog = DFTInputDialog(slab, suggested_dir_name=suggested, parent=self)
        dialog.exec_()

    # ── Export ──

    def export_selected_slab(self):
        slab_index = self.slabs_list_widget.currentRow()
        if slab_index < 0 or slab_index >= len(self.generated_slabs):
            QMessageBox.warning(self, "Error", "No slab selected.")
            return
        try:
            slab = self.generated_slabs[slab_index]
            mat_id = self._get_material_id()

            h = self.h_spin.value()
            k = self.k_spin.value()
            l = self.l_spin.value()
            z_reps = self.zreps_spin.value()
            vac_thick = self.vacuum_spin.value()
            ortho_flag = "ortho" if self.ortho_check.isChecked() else "nonortho"
            vac_mode = self.vac_placement_combo.currentText()
            shift_val = getattr(slab, "shift", slab_index)

            main_name = (
                f"POSCAR_{mat_id}_{h}-{k}-{l}_z{z_reps}_"
                f"vac{vac_thick}_{vac_mode}{ortho_flag}_shift{shift_val}"
            ).replace(".", "-") + ".vasp"

            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save Slab .vasp", main_name,
                "VASP files (*.vasp *.POSCAR);;All Files (*)"
            )
            if not save_path:
                return

            Poscar(slab).write_file(save_path)

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

            QMessageBox.information(self, "Success", msg)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export error:\n{str(e)}")
