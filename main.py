# File: main.py
# -----------------------------------------------------
# A PyQt5 GUI that:
#   1) Reads MP API key from 'mp_api_key.txt' (optional if user only uploads local structures)
#   2) Allows searching Materials Project (new mp_api) OR uploading a local POSCAR as bulk
#   3) Lets user define (h, k, l), slab thickness, vacuum, etc.
#   4) Generates slabs (multiple terminations, orthogonal c-axis, etc.)
#   5) Exports the selected slab to a .vasp file with a suggested filename
#
# Layout Changes:
#   - Top portion is now 3 columns, each in its own QGroupBox:
#       1) Left: "Search Materials Project" panel
#       2) Middle: "OR" label, centered vertically
#       3) Right: "Local Upload" panel with a square upload button + read-only filename box
# -----------------------------------------------------

import sys
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget,
    QSpinBox, QMessageBox, QGroupBox, QCheckBox, QDoubleSpinBox, QComboBox,
    QFileDialog
)

from mp_api.client import MPRester
from pymatgen.core.surface import SlabGenerator
from pymatgen.io.vasp.inputs import Poscar
from pymatgen.core import Structure

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Slab Generator (API or Local Bulk)")

        # 1) Read the API key from local file
        self.api_key = self._read_api_key("mp_api_key.txt")

        # Data holders
        self.structure_docs = []      # List of doc objects from MP
        self.selected_doc_index = None
        self.generated_slabs = []     # List of Slab objects after generation
        self.local_structure = None   # Holds user-uploaded bulk structure (POSCAR)

        #
        # Main layout (vertical)
        #
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        #
        # --- TOP SECTION: 3 columns side by side ---
        #
        top_layout = QHBoxLayout()

        #
        # 1) Left Column: A panel (QGroupBox) for searching Materials Project
        #
        left_col_group = QGroupBox("Search Materials Project")
        left_col_vlayout = QVBoxLayout()

        # -- Row for formula + search
        formula_layout = QHBoxLayout()
        self.formula_label = QLabel("Formula:")
        self.formula_input = QLineEdit()
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_structures)

        formula_layout.addWidget(self.formula_label)
        formula_layout.addWidget(self.formula_input)
        formula_layout.addWidget(self.search_button)

        left_col_vlayout.addLayout(formula_layout)

        # -- List of structures from search
        self.struct_list_widget = QListWidget()
        self.struct_list_widget.itemClicked.connect(self.on_doc_selected)
        left_col_vlayout.addWidget(self.struct_list_widget)

        left_col_group.setLayout(left_col_vlayout)

        #
        # 2) Middle Column: A panel with just a big "OR" in the vertical center
        #
        middle_col_group = QGroupBox()
        middle_col_group.setTitle("")  # or "Alternative"
        middle_col_vlayout = QVBoxLayout()

        # Add stretch on top to push label to center
        middle_col_vlayout.addStretch(1)

        self.or_label = QLabel("OR")
        # Increase font size if desired
        font = self.or_label.font()
        font.setPointSize(14)
        font.setBold(True)
        self.or_label.setFont(font)

        # Center the label horizontally
        middle_col_vlayout.addWidget(self.or_label, alignment=Qt.AlignHCenter)

        middle_col_vlayout.addStretch(1)
        middle_col_group.setLayout(middle_col_vlayout)

        #
        # 3) Right Column: A panel for uploading a local file
        #
        right_col_group = QGroupBox("Local Upload")
        right_col_vlayout = QVBoxLayout()

        # Add stretch to push the content to the middle
        right_col_vlayout.addStretch(1)

        self.upload_button = QPushButton("Upload")
        self.upload_button.setFixedSize(60, 60)  # make button square
        self.upload_button.clicked.connect(self.upload_bulk_structure)
        # center horizontally
        right_col_vlayout.addWidget(self.upload_button, alignment=Qt.AlignHCenter)

        # A read-only text box for the chosen filename
        self.filename_line = QLineEdit()
        self.filename_line.setPlaceholderText("No file selected")
        self.filename_line.setReadOnly(True)
        # center horizontally
        right_col_vlayout.addWidget(self.filename_line, alignment=Qt.AlignHCenter)

        # Add stretch at bottom
        right_col_vlayout.addStretch(1)

        right_col_group.setLayout(right_col_vlayout)

        #
        # Combine the 3 columns in top_layout
        #
        # You can tweak the stretch factors if you want different widths.
        top_layout.addWidget(left_col_group, stretch=7)
        top_layout.addWidget(middle_col_group, stretch=1)
        top_layout.addWidget(right_col_group, stretch=3)

        main_layout.addLayout(top_layout)

        #
        # --- SLAB GENERATION OPTIONS (below top section) ---
        #
        slab_options_group = QGroupBox("Slab Generation Options")
        slab_options_layout = QHBoxLayout()

        # Miller indices
        slab_options_layout.addWidget(QLabel("h:"))
        self.h_spin = QSpinBox()
        self.h_spin.setRange(-10, 10)
        self.h_spin.setValue(0)
        slab_options_layout.addWidget(self.h_spin)

        slab_options_layout.addWidget(QLabel("k:"))
        self.k_spin = QSpinBox()
        self.k_spin.setRange(-10, 10)
        self.k_spin.setValue(0)
        slab_options_layout.addWidget(self.k_spin)

        slab_options_layout.addWidget(QLabel("l:"))
        self.l_spin = QSpinBox()
        self.l_spin.setRange(-10, 10)
        self.l_spin.setValue(1)
        slab_options_layout.addWidget(self.l_spin)

        # Slab thickness
        slab_options_layout.addWidget(QLabel("Slab (Å):"))
        self.slab_thick_spin = QDoubleSpinBox()
        self.slab_thick_spin.setRange(1.0, 100.0)
        self.slab_thick_spin.setValue(8.0)
        self.slab_thick_spin.setSingleStep(0.5)
        slab_options_layout.addWidget(self.slab_thick_spin)

        # Vacuum thickness
        slab_options_layout.addWidget(QLabel("Vacuum (Å):"))
        self.vacuum_spin = QDoubleSpinBox()
        self.vacuum_spin.setRange(0.0, 100.0)
        self.vacuum_spin.setValue(10.0)
        self.vacuum_spin.setSingleStep(0.5)
        slab_options_layout.addWidget(self.vacuum_spin)

        # Vacuum placement
        slab_options_layout.addWidget(QLabel("Vacuum placement:"))
        self.vac_placement_combo = QComboBox()
        self.vac_placement_combo.addItems(["top-only", "centered"])
        slab_options_layout.addWidget(self.vac_placement_combo)

        # All terminations checkbox
        self.all_terminations_check = QCheckBox("All Terminations?")
        slab_options_layout.addWidget(self.all_terminations_check)

        # Force orthogonal c-axis
        self.ortho_check = QCheckBox("Orthogonal c-axis?")
        slab_options_layout.addWidget(self.ortho_check)

        # Generate Slabs button
        self.generate_slabs_button = QPushButton("Generate Slabs")
        self.generate_slabs_button.clicked.connect(self.generate_slabs)
        slab_options_layout.addWidget(self.generate_slabs_button)

        slab_options_group.setLayout(slab_options_layout)
        main_layout.addWidget(slab_options_group)

        #
        # --- SLABS LIST & EXPORT BUTTON ---
        #
        self.slabs_list_widget = QListWidget()
        main_layout.addWidget(self.slabs_list_widget)

        self.export_button = QPushButton("Export Selected Slab to .vasp")
        self.export_button.clicked.connect(self.export_selected_slab)
        main_layout.addWidget(self.export_button)

    def _read_api_key(self, path):
        """
        Reads the API key/license from the specified file.
        Returns a stripped string, or empty if file not found.
        """
        if not os.path.exists(path):
            return ""
        with open(path, "r") as f:
            key = f.read().strip()
        return key

    def search_structures(self):
        """Search the Materials Project for the given formula."""
        formula = self.formula_input.text().strip()
        if not formula:
            QMessageBox.warning(self, "Error", "Please enter a formula or upload a bulk file.")
            return

        if not self.api_key:
            QMessageBox.warning(self, "Warning",
                                "No API key found. Please create 'mp_api_key.txt' or rely on local bulk upload.")
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

            # Clear any previously uploaded local structure
            self.local_structure = None
            self.selected_doc_index = None

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred:\n{str(e)}")

    def on_doc_selected(self, item):
        """Stores index of the selected doc for later use."""
        self.selected_doc_index = self.struct_list_widget.currentRow()

    def upload_bulk_structure(self):
        """
        Allows user to upload a local POSCAR/CONTCAR file to serve as the 'bulk structure'.
        """
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
                # Show the selected file name in the read-only text box
                self.filename_line.setText(os.path.basename(file_path))

                # Clear the doc list so we don't confuse the user
                self.struct_list_widget.clear()
                self.structure_docs.clear()
                self.selected_doc_index = None

                QMessageBox.information(self, "Success",
                                        f"Local bulk structure loaded from:\n{file_path}\n"
                                        f"({len(struct.sites)} atoms).")
            except Exception as ex:
                QMessageBox.critical(self, "Error", f"Failed to read structure:\n{str(ex)}")

    def generate_slabs(self):
        """
        Creates slab(s) from either:
          1) the user-selected doc from MP, or
          2) the locally uploaded bulk structure (self.local_structure).
        If neither is available, show an error.
        """
        # Decide which structure to use
        chosen_structure = None

        if self.local_structure is not None:
            chosen_structure = self.local_structure.copy()
        else:
            # If no local structure, try the MP doc
            if self.selected_doc_index is not None and self.selected_doc_index >= 0:
                doc = self.structure_docs[self.selected_doc_index]
                if doc.structure:
                    chosen_structure = doc.structure.copy()

        if chosen_structure is None:
            QMessageBox.warning(self, "Error",
                                "No bulk structure available. "
                                "Please either select a result from MP search or upload a local POSCAR.")
            return

        # Gather user inputs
        h = self.h_spin.value()
        k = self.k_spin.value()
        l = self.l_spin.value()
        slab_thick = self.slab_thick_spin.value()
        vac_thick = self.vacuum_spin.value()
        all_terms = self.all_terminations_check.isChecked()
        force_ortho = self.ortho_check.isChecked()
        vac_placement = self.vac_placement_combo.currentText()
        center_slab = (vac_placement == "centered")

        # Clear old results
        self.slabs_list_widget.clear()
        self.generated_slabs.clear()

        # Create SlabGenerator
        try:
            slab_gen = SlabGenerator(
                initial_structure=chosen_structure,
                miller_index=(h, k, l),
                min_slab_size=slab_thick,
                min_vacuum_size=vac_thick,
                center_slab=center_slab
            )

            if all_terms:
                # Generate all possible terminations/shifts
                slab_list = slab_gen.get_slabs(symmetrize=False)
            else:
                slab_list = [slab_gen.get_slab()]

            if not slab_list:
                QMessageBox.information(self, "No Slab Generated",
                                        "No slabs were generated with these parameters.")
                return

            # If user wants orthogonal c-axis, apply get_orthogonal_c_slab
            final_slabs = []
            for i, slab in enumerate(slab_list):
                if force_ortho:
                    slab = slab.get_orthogonal_c_slab()
                final_slabs.append(slab)

            self.generated_slabs = final_slabs

            # Populate the list widget
            for i, slab in enumerate(final_slabs):
                shift_val = getattr(slab, "shift", float(i))
                item_str = f"Slab {i}: {slab.composition.reduced_formula}, shift={shift_val:.2f}"
                if force_ortho:
                    item_str += " (Orthogonal)"
                if center_slab:
                    item_str += " (Centered)"
                else:
                    item_str += " (Top-only)"
                self.slabs_list_widget.addItem(item_str)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Slab generation error:\n{str(e)}")

    def export_selected_slab(self):
        """
        Exports the user-chosen slab to a .vasp file, with a suggested filename
        that includes shift and other settings (and replaces '.' with '-').
        """
        slab_index = self.slabs_list_widget.currentRow()
        if slab_index < 0 or slab_index >= len(self.generated_slabs):
            QMessageBox.warning(self, "Error", "No slab selected.")
            return

        try:
            slab = self.generated_slabs[slab_index]

            # Decide on naming info
            # If we used local structure, mat_id might be 'LOCAL'
            # Otherwise, we read from the doc
            mat_id = "LOCAL"
            if (self.local_structure is None and
                self.selected_doc_index is not None and
                0 <= self.selected_doc_index < len(self.structure_docs)):
                doc = self.structure_docs[self.selected_doc_index]
                mat_id = doc.material_id or "UNKNOWN"

            h = self.h_spin.value()
            k = self.k_spin.value()
            l = self.l_spin.value()
            slab_thick = self.slab_thick_spin.value()
            vac_thick = self.vacuum_spin.value()
            ortho_flag = "_ortho" if self.ortho_check.isChecked() else ""
            vac_mode = self.vac_placement_combo.currentText()  # "top-only" or "centered"
            shift_val = getattr(slab, "shift", slab_index)

            # Create suggested filename
            suggested_name = (
                f"POSCAR_{mat_id}_{h}-{k}-{l}_slab{slab_thick}_"
                f"vac{vac_thick}_{vac_mode}{ortho_flag}_shift{shift_val}"
            ).replace(".", "-") + ".vasp"

            # Prompt user to save
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Slab .vasp",
                suggested_name,
                "VASP files (*.vasp *.POSCAR);;All Files (*)"
            )
            if not save_path:
                return  # user canceled

            poscar = Poscar(slab)
            poscar.write_file(save_path)

            QMessageBox.information(self, "Success",
                                    f"Exported Slab {slab_index} to:\n{save_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export error:\n{str(e)}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
