# File: main.py
# -----------------------------------------------------
# A PyQt5 GUI that:
#   - Reads MP API key from mp_api_key.txt (if present).
#   - Lets user specify (h,k,l), Z Reps, vacuum, etc.
#   - Orients the structure so (h,k,l) is along z, replicates along that new z,
#     then final-slab with (0,0,1) for vacuum & terminations.
#   - Preserves "All Terminations?", "Do Comparison?", "Generate Cleaved Files?" etc.
#   - Exports the main slab & optionally top/bottom slices.
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
from pymatgen.core.surface import SlabGenerator
from pymatgen.io.vasp.inputs import Poscar
from pymatgen.analysis.structure_matcher import StructureMatcher


########################################
# Helper Methods
########################################

def oriented_slab_replication(
    structure: Structure,
    h: int,
    k: int,
    l: int,
    z_reps: int,
    min_vac: float,
    center_slab: bool,
    all_terminations: bool,
    force_ortho: bool
):
    """
    1) Orient the bulk so (h,k,l) is along new z-axis (no vacuum, min_slab=1).
    2) Replicate that oriented structure along new z by z_reps.
    3) Final SlabGenerator with (0,0,1), min_slab=1, min_vac=..., center_slab=...,
       to produce the vacuum and terminations.
    4) If force_ortho, do get_orthogonal_c_slab().

    Returns a list of Slab objects (one or multiple if all_terminations=True).
    """

    # Step 1: SlabGenerator with (h,k,l), min_slab=1, vac=0 => orientation matrix
    orient_gen = SlabGenerator(
        initial_structure=structure.copy(),
        miller_index=(h,k,l),
        min_slab_size=1.0,
        min_vacuum_size=0.0,
        center_slab=False
    )
    # Just take one default slab from that generator to get the oriented structure
    oriented_slab = orient_gen.get_slab()  # or get_slabs()[0]

    # Step 2: Replicate oriented slab along its new c-axis
    oriented_slab.make_supercell([1, 1, z_reps])  # replicate in z

    # Step 3: Another SlabGenerator, but now normal is (0,0,1),
    # 'oriented_slab' already has c-axis normal to the original (h,k,l).
    final_gen = SlabGenerator(
        initial_structure=oriented_slab,
        miller_index=(0,0,1),
        min_slab_size=1.0,       # thickness effectively from replication
        min_vacuum_size=min_vac,
        center_slab=center_slab
    )

    if all_terminations:
        slabs = final_gen.get_slabs(symmetrize=False)
    else:
        slabs = [final_gen.get_slab()]

    # Step 4: If force_ortho, apply get_orthogonal_c_slab() to each
    results = []
    for s in slabs:
        if force_ortho:
            s = s.get_orthogonal_c_slab()
        results.append(s)

    return results

def cut_out_z_region(structure, zmin, zmax):
    """
    Return new Structure with sites having z in [zmin, zmax].
    """
    struct = structure.copy()
    new_sites = []
    for site in struct:
        z = site.coords[2]
        if zmin <= z <= zmax:
            new_sites.append(site)
    if not new_sites:
        return None
    from pymatgen.core import Structure
    new_struct = Structure(lattice=struct.lattice, species=[], coords=[])
    for s in new_sites:
        new_struct.append(s.species, s.coords, coords_are_cartesian=True)
    return new_struct

def rotate_bottom_180(structure):
    """
    Rotate the structure 180° around the y-axis => flips it upside down.
    """
    struct = structure.copy()
    rotation_matrix = np.array([
        [-1.0,  0.0,  0.0],
        [ 0.0,  1.0,  0.0],
        [ 0.0,  0.0, -1.0]
    ], dtype=float)
    new_sites = []
    for site in struct:
        coords = site.coords
        new_coords = rotation_matrix.dot(coords)
        new_sites.append((site.species, new_coords))
    from pymatgen.core import Structure
    rotated = Structure(lattice=struct.lattice, species=[], coords=[])
    for species, c in new_sites:
        rotated.append(species, c, coords_are_cartesian=True)
    return rotated

def compare_structures(top_struct, bottom_struct):
    """
    Use StructureMatcher to see if they match, returning (bool, rmsd).
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
    else:
        return (False, None)


########################################
# MAIN WINDOW (GUI)
########################################

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Slab Generator: replicate along slab normal (even if l=0)")

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
        # 1) TOP SECTION: Search / OR / Upload with custom stretches
        #
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

        top_layout.addWidget(left_col_group, stretch=6)   # bigger
        top_layout.addWidget(middle_col_group, stretch=1) # small for "OR"
        top_layout.addWidget(right_col_group, stretch=2)  # smaller
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
        self.vacuum_spin.setSingleStep(0.5)
        slab_layout.addWidget(self.vacuum_spin)

        slab_layout.addWidget(QLabel("Vac Placement:"))
        self.vac_placement_combo = QComboBox()
        self.vac_placement_combo.addItems(["top-only","centered"])
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

        self.comparison_check = QCheckBox("Do Comparison? (Slow)")
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


    ######################################################
    # UI Logic
    ######################################################

    def _toggle_comparison_options(self):
        do_compare = self.comparison_check.isChecked()
        self.compare_depth_spin.setEnabled(do_compare)
        self.generate_cleaves_check.setEnabled(do_compare)

    def _read_api_key(self, path):
        if not os.path.exists(path):
            return ""
        with open(path, "r") as f:
            return f.read().strip()

    ########################################
    # SEARCH & UPLOAD
    ########################################
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
                QMessageBox.information(self, "Success",
                    f"Local bulk structure loaded from:\n{file_path}\n({len(struct.sites)} atoms).")
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
            if (self.selected_doc_index is not None and
                0 <= self.selected_doc_index < len(self.structure_docs)):
                doc = self.structure_docs[self.selected_doc_index]
                if doc.structure:
                    chosen_structure = doc.structure.copy()

        if chosen_structure is None:
            QMessageBox.warning(self, "Error",
                                "No bulk structure. Select from MP or upload a POSCAR.")
            return

        h = self.h_spin.value()
        k = self.k_spin.value()
        l = self.l_spin.value()
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
            # Use the 2-step orientation approach
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

            # Optionally do top/bottom comparison
            for i, slab in enumerate(final_slabs):
                shift_val = getattr(slab, "shift", float(i))
                label_str = ""

                if do_compare:
                    # slice top/bottom
                    all_z = [site.coords[2] for site in slab]
                    z_min, z_max = min(all_z), max(all_z)
                    topZ1 = z_max - compare_depth
                    bottomZ2 = z_min + compare_depth
                    top_struct = cut_out_z_region(slab, topZ1, z_max)
                    bottom_struct = cut_out_z_region(slab, z_min, bottomZ2)

                    bottom_rot = None
                    if bottom_struct:
                        bottom_rot = rotate_bottom_180(bottom_struct)

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
    # EXPORT SLAB
    ########################################
    def export_selected_slab(self):
        slab_index = self.slabs_list_widget.currentRow()
        if slab_index < 0 or slab_index >= len(self.generated_slabs):
            QMessageBox.warning(self, "Error", "No slab selected.")
            return
        try:
            slab = self.generated_slabs[slab_index]

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
                "Save Slab .vasp",
                main_name,
                "VASP files (*.vasp *.POSCAR);;All Files (*)"
            )
            if not save_path:
                return

            Poscar(slab).write_file(save_path)

            do_compare = self.comparison_check.isChecked()
            do_cleaves = self.generate_cleaves_check.isChecked()

            if do_compare and do_cleaves:
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

                msg = f"Exported slab => {save_path}\nTop => {top_path}\nBottom(rot) => {bottom_path}"
            else:
                msg = f"Exported slab => {save_path}"

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
