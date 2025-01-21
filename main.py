# File: main.py
# -----------------------------------------------------
# A PyQt5 GUI that:
#   1) Reads MP API key from 'mp_api_key.txt' (optional).
#   2) Allows searching Materials Project (new mp_api) OR uploading a local POSCAR as bulk.
#   3) Lets user define (h, k, l), Z Repetitions, vacuum thickness, etc.
#   4) An "Advanced Options" panel with:
#       - All Terminations?
#       - Do Comparison? (check to enable top/bottom matching)
#       - Generate separate cleaved files? (enabled if comparison is checked)
#       - Comparison Depth (enabled if comparison is checked)
#   5) The Generate Slabs button is under this advanced panel.
#   6) If "Do Comparison?" is selected, we do top/bottom slicing, rotate, and structure matching.
#   7) If "Generate separate cleaved files?" is also selected, we export the top/bottom as .vasp files upon saving.
# -----------------------------------------------------

import sys
import os
import numpy as np

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget,
    QSpinBox, QMessageBox, QGroupBox, QCheckBox, QDoubleSpinBox, QComboBox,
    QFileDialog
)

from mp_api.client import MPRester
from pymatgen.core import Structure
from pymatgen.io.vasp.inputs import Poscar
from pymatgen.core.surface import SlabGenerator
from pymatgen.analysis.structure_matcher import StructureMatcher

# Helper methods (replicate_bulk, cut_out_z_region, rotate_bottom_180, compare_structures)
# omitted here for brevity. Integrate from your existing logic.

############################################
# Example stubs for the required helpers:
############################################
def replicate_bulk(structure, z_reps=1):
    struct = structure.copy()
    struct.make_supercell([1,1,z_reps])
    return struct

def cut_out_z_region(structure, zmin, zmax):
    struct = structure.copy()
    new_sites = []
    for site in struct.sites:
        z = site.coords[2]
        if zmin <= z <= zmax:
            new_sites.append(site)
    if not new_sites:
        return None
    new_struct = Structure(lattice=struct.lattice, species=[], coords=[])
    for s in new_sites:
        new_struct.append(s.species, s.coords, coords_are_cartesian=True)
    return new_struct

def rotate_bottom_180(structure):
    struct = structure.copy()
    rotation_matrix = np.array([
        [-1.0,  0.0,  0.0],
        [ 0.0,  1.0,  0.0],
        [ 0.0,  0.0, -1.0]
    ], dtype=float)
    new_sites = []
    for site in struct.sites:
        coords = site.coords
        new_coords = rotation_matrix.dot(coords)
        new_sites.append((site.species, new_coords))
    rotated = Structure(
        lattice=struct.lattice,
        species=[],
        coords=[]
    )
    for species, c in new_sites:
        rotated.append(species, c, coords_are_cartesian=True)
    return rotated

def compare_structures(top_struct, bottom_struct):
    if (top_struct is None) or (bottom_struct is None):
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
    else:
        return (False, None)


############################################
# MAIN WINDOW (GUI)
############################################

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Slab Generator with Single-line Advanced Options")

        # Read MP API key
        self.api_key = self._read_api_key("mp_api_key.txt")

        # Data holders
        self.structure_docs = []
        self.selected_doc_index = None
        self.generated_slabs = []
        self.local_structure = None

        # MAIN layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        #
        # 1) TOP SECTION: 3 columns => (search:6), (OR:1), (upload:2)
        #
        top_layout = QHBoxLayout()

        # 1A) Left (Search)
        left_col_group = QGroupBox("Search Materials Project")
        left_col_layout = QVBoxLayout()

        formula_layout = QHBoxLayout()
        self.formula_label = QLabel("Formula:")
        self.formula_input = QLineEdit()
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_structures)

        formula_layout.addWidget(self.formula_label)
        formula_layout.addWidget(self.formula_input)
        formula_layout.addWidget(self.search_button)
        left_col_layout.addLayout(formula_layout)

        self.struct_list_widget = QListWidget()
        self.struct_list_widget.itemClicked.connect(self.on_doc_selected)
        left_col_layout.addWidget(self.struct_list_widget)

        left_col_group.setLayout(left_col_layout)

        # 1B) Middle ("OR")
        middle_col_group = QGroupBox()
        middle_col_group.setTitle("")  # no title
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

        # 1C) Right (Upload)
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

        # Add them with custom stretches
        top_layout.addWidget(left_col_group, stretch=6)
        top_layout.addWidget(middle_col_group, stretch=1)
        top_layout.addWidget(right_col_group, stretch=2)

        main_layout.addLayout(top_layout)

        #
        # 2) BASIC SLAB OPTIONS
        #
        slab_options_group = QGroupBox("Basic Slab Options")
        slab_layout = QHBoxLayout()

        slab_layout.addWidget(QLabel("h:"))
        self.h_spin = QSpinBox()
        self.h_spin.setRange(-10,10)
        self.h_spin.setValue(0)
        slab_layout.addWidget(self.h_spin)

        slab_layout.addWidget(QLabel("k:"))
        self.k_spin = QSpinBox()
        self.k_spin.setRange(-10,10)
        self.k_spin.setValue(0)
        slab_layout.addWidget(self.k_spin)

        slab_layout.addWidget(QLabel("l:"))
        self.l_spin = QSpinBox()
        self.l_spin.setRange(-10,10)
        self.l_spin.setValue(1)
        slab_layout.addWidget(self.l_spin)

        slab_layout.addWidget(QLabel("Z Reps:"))
        self.zreps_spin = QSpinBox()
        self.zreps_spin.setRange(1, 50)
        self.zreps_spin.setValue(1)
        slab_layout.addWidget(self.zreps_spin)

        slab_layout.addWidget(QLabel("Vacuum (Å):"))
        self.vacuum_spin = QDoubleSpinBox()
        self.vacuum_spin.setRange(0.0, 100.0)
        self.vacuum_spin.setValue(10.0)
        slab_layout.addWidget(self.vacuum_spin)

        slab_layout.addWidget(QLabel("Vac. placement:"))
        self.vac_placement_combo = QComboBox()
        self.vac_placement_combo.addItems(["top-only", "centered"])
        slab_layout.addWidget(self.vac_placement_combo)

        self.ortho_check = QCheckBox("Orthogonal c-axis?")
        slab_layout.addWidget(self.ortho_check)

        slab_options_group.setLayout(slab_layout)
        main_layout.addWidget(slab_options_group)

        #
        # 3) ADVANCED OPTIONS (Single Row)
        #
        adv_options_group = QGroupBox("Advanced Options")
        adv_layout = QHBoxLayout()

        self.all_terminations_check = QCheckBox("All Terminations?")
        adv_layout.addWidget(self.all_terminations_check)

        self.comparison_check = QCheckBox("Do Comparison?")
        self.comparison_check.stateChanged.connect(self._toggle_comparison_options)
        adv_layout.addWidget(self.comparison_check)

        self.generate_cleaves_check = QCheckBox("Separate top/bot files?")
        self.generate_cleaves_check.setEnabled(False)
        adv_layout.addWidget(self.generate_cleaves_check)

        adv_layout.addWidget(QLabel("Depth (Å):"))
        self.compare_depth_spin = QDoubleSpinBox()
        self.compare_depth_spin.setRange(0.0, 100.0)
        self.compare_depth_spin.setValue(5.0)
        self.compare_depth_spin.setEnabled(False)
        adv_layout.addWidget(self.compare_depth_spin)

        # The "Generate Slabs" button at the end
        self.generate_slabs_button = QPushButton("Generate Slabs")
        self.generate_slabs_button.clicked.connect(self.generate_slabs)
        adv_layout.addWidget(self.generate_slabs_button)

        adv_options_group.setLayout(adv_layout)
        main_layout.addWidget(adv_options_group)

        #
        # 4) SLABS LIST + EXPORT
        #
        self.slabs_list_widget = QListWidget()
        main_layout.addWidget(self.slabs_list_widget)

        self.export_button = QPushButton("Export Selected Slab")
        self.export_button.clicked.connect(self.export_selected_slab)
        main_layout.addWidget(self.export_button)
        
    def _toggle_comparison_options(self):
        """Enable or disable the comparison depth and cleaves checkbox
           based on the 'Do Comparison?' checkbox."""
        do_compare = self.comparison_check.isChecked()
        self.compare_depth_spin.setEnabled(do_compare)
        self.generate_cleaves_check.setEnabled(do_compare)

    def _read_api_key(self, path):
        if not os.path.exists(path):
            return ""
        with open(path, "r") as f:
            key = f.read().strip()
        return key

    ########################################
    # MATERIALS PROJECT SEARCH
    ########################################
    def search_structures(self):
        formula = self.formula_input.text().strip()
        if not formula:
            QMessageBox.warning(self, "Error", "Please enter a formula or upload a bulk file.")
            return

        if not self.api_key:
            QMessageBox.warning(self, "Warning",
                                "No API key found. Provide mp_api_key.txt or use local bulk upload.")
            return

        try:
            self.struct_list_widget.clear()
            self.structure_docs.clear()
            with MPRester(self.api_key) as mpr:
                docs = mpr.materials.search(formula=formula)

            if not docs:
                QMessageBox.information(self, "No Results", f"No structures found for '{formula}'.")
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
            QMessageBox.critical(self, "Error", f"An error occurred:\n{str(e)}")

    def on_doc_selected(self, item):
        self.selected_doc_index = self.struct_list_widget.currentRow()

    ########################################
    # LOCAL UPLOAD
    ########################################
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

                QMessageBox.information(
                    self, "Success",
                    f"Local bulk structure loaded from:\n{file_path}\n({len(struct.sites)} atoms)."
                )
            except Exception as ex:
                QMessageBox.critical(self, "Error", f"Failed to read structure:\n{str(ex)}")

    ########################################
    # GENERATE SLABS
    ########################################
    def generate_slabs(self):
        chosen_structure = None
        if self.local_structure is not None:
            chosen_structure = self.local_structure.copy()
        else:
            if self.selected_doc_index is not None and self.selected_doc_index >= 0:
                doc = self.structure_docs[self.selected_doc_index]
                if doc.structure:
                    chosen_structure = doc.structure.copy()

        if chosen_structure is None:
            QMessageBox.warning(self, "Error",
                                "No bulk structure available. "
                                "Either select from MP or upload a local POSCAR.")
            return

        h = self.h_spin.value()
        k = self.k_spin.value()
        l = self.l_spin.value()
        z_reps = self.zreps_spin.value()
        vac_thick = self.vacuum_spin.value()
        center_slab = (self.vac_placement_combo.currentText() == "centered")
        do_term = self.all_terminations_check.isChecked()
        do_compare = self.comparison_check.isChecked()
        compare_depth = self.compare_depth_spin.value()
        force_ortho = self.ortho_check.isChecked()

        self.slabs_list_widget.clear()
        self.generated_slabs.clear()

        try:
            # replicate bulk
            from_pymatgen = replicate_bulk(chosen_structure, z_reps)

            # Build slabs
            slab_gen = SlabGenerator(
                initial_structure=from_pymatgen,
                miller_index=(h,k,l),
                min_slab_size=1.0,
                min_vacuum_size=vac_thick,
                center_slab=center_slab
            )

            if do_term:
                slab_list = slab_gen.get_slabs(symmetrize=False)
            else:
                slab_list = [slab_gen.get_slab()]

            if not slab_list:
                QMessageBox.information(self, "No Slab Generated",
                                        "No slabs were generated with these parameters.")
                return

            final_slabs = []
            for i, slab in enumerate(slab_list):
                if force_ortho:
                    slab = slab.get_orthogonal_c_slab()
                final_slabs.append(slab)

            self.generated_slabs = final_slabs

            # If do_compare is not checked, we won't do top/bottom comparison
            for i, slab in enumerate(final_slabs):
                shift_val = getattr(slab, "shift", float(i))
                label_str = ""

                if do_compare:
                    # Do top/bottom extraction and matching
                    all_z = [site.coords[2] for site in slab]
                    z_min, z_max = min(all_z), max(all_z)
                    topZ1 = z_max - compare_depth
                    bottomZ2 = z_min + compare_depth
                    top_struct = cut_out_z_region(slab, topZ1, z_max)
                    bottom_struct = cut_out_z_region(slab, z_min, bottomZ2)
                    if bottom_struct:
                        bottom_rot = rotate_bottom_180(bottom_struct)
                    else:
                        bottom_rot = None

                    match_bool, rmsd_val = compare_structures(top_struct, bottom_rot)
                    if match_bool:
                        label_str = f"(match, RMSD={rmsd_val:.2f} Å)"
                    else:
                        label_str = "(no match)"

                item_str = f"Slab {i}: {slab.composition.reduced_formula}, shift={shift_val:.2f} {label_str}"
                self.slabs_list_widget.addItem(item_str)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Slab generation error:\n{str(e)}")

    ########################################
    # EXPORT SELECTED SLAB
    ########################################
    def export_selected_slab(self):
        slab_index = self.slabs_list_widget.currentRow()
        if slab_index < 0 or slab_index >= len(self.generated_slabs):
            QMessageBox.warning(self, "Error", "No slab selected.")
            return

        try:
            slab = self.generated_slabs[slab_index]

            # Build a suggested filename
            mat_id = "LOCAL"
            if (self.local_structure is None and
                self.selected_doc_index is not None and
                0 <= self.selected_doc_index < len(self.structure_docs)):
                doc = self.structure_docs[self.selected_doc_index]
                mat_id = doc.material_id or "UNKNOWN"

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
                self,
                "Save Slab",
                main_name,
                "VASP files (*.vasp *.POSCAR);;All Files (*)"
            )
            if not save_path:
                return

            # Write main slab
            Poscar(slab).write_file(save_path)

            # Optionally generate top/bottom files if:
            # 1) "Do Comparison?" is checked, and
            # 2) "Generate separate top & bottom files?" is checked
            if self.comparison_check.isChecked() and self.generate_cleaves_check.isChecked():
                compare_depth = self.compare_depth_spin.value()
                all_z = [site.coords[2] for site in slab]
                z_min, z_max = min(all_z), max(all_z)
                topZ1 = z_max - compare_depth
                bottomZ2 = z_min + compare_depth

                top_struct = cut_out_z_region(slab, topZ1, z_max)
                bottom_struct = cut_out_z_region(slab, z_min, bottomZ2)
                bottom_rot = None
                if bottom_struct:
                    bottom_rot = rotate_bottom_180(bottom_struct)

                base_no_ext = os.path.splitext(save_path)[0]
                top_path = f"{base_no_ext}_top.vasp"
                bottom_path = f"{base_no_ext}_bottom_rot.vasp"

                if top_struct and len(top_struct) > 0:
                    Poscar(top_struct).write_file(top_path)
                if bottom_rot and len(bottom_rot) > 0:
                    Poscar(bottom_rot).write_file(bottom_path)

                msg = f"Exported slab to:\n{save_path}"
                msg += f"\nTop region => {top_path}"
                msg += f"\nBottom region (rotated) => {bottom_path}"
            else:
                msg = f"Exported slab to:\n{save_path}"

            QMessageBox.information(self, "Success", msg)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export error:\n{str(e)}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
