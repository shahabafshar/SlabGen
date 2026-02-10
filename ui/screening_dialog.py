import csv
import os
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QDoubleSpinBox, QCheckBox, QComboBox, QPushButton,
    QProgressBar, QTableWidget, QTableWidgetItem, QGroupBox,
    QFileDialog, QMessageBox, QHeaderView,
)
from PySide6.QtGui import QColor

from pymatgen.io.vasp.inputs import Poscar
from core.screening import SurfaceScreener


class ScreeningWorker(QThread):
    """Run surface screening in a background thread."""
    progress = Signal(int, int)  # current, total
    finished = Signal(list)      # results
    error = Signal(str)

    def __init__(self, screener):
        super().__init__()
        self.screener = screener

    def run(self):
        try:
            results = self.screener.screen(
                progress_callback=lambda cur, tot: self.progress.emit(cur, tot)
            )
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class ScreeningDialog(QDialog):
    """Dialog for batch surface screening with results table."""

    # Signal emitted when user wants to load a surface back into main window
    load_surface = Signal(object, tuple)  # (slab, miller_index)

    def __init__(self, structure, parent=None, initial_params=None):
        super().__init__(parent)
        self.setWindowTitle("Surface Screening")
        self.setMinimumSize(900, 600)
        self.structure = structure
        self.results = []
        self._worker = None

        layout = QVBoxLayout()
        self.setLayout(layout)

        # ── Parameters ──
        params_group = QGroupBox("Screening Parameters")
        params_layout = QHBoxLayout()

        params_layout.addWidget(QLabel("Max Miller Index:"))
        self.max_index_spin = QSpinBox()
        self.max_index_spin.setRange(1, 4)
        self.max_index_spin.setValue(2)
        params_layout.addWidget(self.max_index_spin)

        params_layout.addWidget(QLabel("Z Reps:"))
        self.zreps_spin = QSpinBox()
        self.zreps_spin.setRange(1, 50)
        self.zreps_spin.setValue(3)
        params_layout.addWidget(self.zreps_spin)

        params_layout.addWidget(QLabel("Vacuum (\u00c5):"))
        self.vacuum_spin = QDoubleSpinBox()
        self.vacuum_spin.setRange(0.0, 100.0)
        self.vacuum_spin.setValue(10.0)
        self.vacuum_spin.setSingleStep(0.5)
        params_layout.addWidget(self.vacuum_spin)

        params_layout.addWidget(QLabel("Placement:"))
        self.placement_combo = QComboBox()
        self.placement_combo.addItems(["top-only", "centered"])
        params_layout.addWidget(self.placement_combo)

        self.ortho_check = QCheckBox("Ortho c-axis?")
        params_layout.addWidget(self.ortho_check)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # UX #9: Apply initial params from main window
        if initial_params:
            self.zreps_spin.setValue(initial_params.get("z_reps", 3))
            self.vacuum_spin.setValue(initial_params.get("vacuum", 10.0))
            placement = initial_params.get("placement", "top-only")
            idx = self.placement_combo.findText(placement)
            if idx >= 0:
                self.placement_combo.setCurrentIndex(idx)
            self.ortho_check.setChecked(initial_params.get("ortho", False))

        # ── Run / Progress ──
        run_layout = QHBoxLayout()
        self.run_button = QPushButton("Run Screening")
        self.run_button.clicked.connect(self._run_screening)
        run_layout.addWidget(self.run_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        run_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        run_layout.addWidget(self.status_label)
        layout.addLayout(run_layout)

        # ── Results Table ──
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Miller Index", "Shift", "Atoms", "Surface Area (\u00c5\u00b2)",
            "Symmetric", "Formula"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        # ── Action Buttons ──
        action_layout = QHBoxLayout()

        self.export_csv_button = QPushButton("Export to CSV")
        self.export_csv_button.clicked.connect(self._export_csv)
        self.export_csv_button.setEnabled(False)
        action_layout.addWidget(self.export_csv_button)

        # Feature #19: Batch POSCAR export
        self.export_poscar_button = QPushButton("Export All as POSCAR")
        self.export_poscar_button.clicked.connect(self._export_all_poscar)
        self.export_poscar_button.setEnabled(False)
        action_layout.addWidget(self.export_poscar_button)

        self.load_button = QPushButton("Load Selected in Main Window")
        self.load_button.clicked.connect(self._load_selected)
        self.load_button.setEnabled(False)
        action_layout.addWidget(self.load_button)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        action_layout.addWidget(close_button)

        layout.addLayout(action_layout)

    def _run_screening(self):
        self.run_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Screening...")
        self.table.setRowCount(0)
        self.results.clear()

        screener = SurfaceScreener(
            structure=self.structure,
            max_index=self.max_index_spin.value(),
            z_reps=self.zreps_spin.value(),
            vacuum=self.vacuum_spin.value(),
            center_slab=(self.placement_combo.currentText() == "centered"),
            force_ortho=self.ortho_check.isChecked(),
        )

        self._worker = ScreeningWorker(screener)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current, total):
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
            self.status_label.setText(
                f"Processing Miller index {current}/{total}..."
            )

    def _on_finished(self, results):
        self.results = results
        self._populate_table(results)
        self.run_button.setEnabled(True)
        self.export_csv_button.setEnabled(bool(results))
        self.export_poscar_button.setEnabled(bool(results))
        self.load_button.setEnabled(bool(results))
        self.progress_bar.setValue(self.progress_bar.maximum())

        n_surfaces = len(set(r['miller_str'] for r in results))
        status = f"Done. {len(results)} terminations across {n_surfaces} surfaces."

        # Report any surfaces that failed to generate
        failures = getattr(self._worker.screener, "failures", [])
        if failures:
            fail_list = ", ".join(
                f"({h},{k},{l})" for h, k, l in (f["miller"] for f in failures)
            )
            status += f"  [{len(failures)} failed: {fail_list}]"

        self.status_label.setText(status)

    def _on_error(self, error_msg):
        self.run_button.setEnabled(True)
        self.status_label.setText("Error!")
        QMessageBox.critical(self, "Screening Error", error_msg)

    def _populate_table(self, results):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(results))

        for row, r in enumerate(results):
            # Store original index in first column's UserRole so sorting
            # doesn't break the mapping between visual row and results list
            miller_item = QTableWidgetItem(r["miller_str"])
            miller_item.setData(Qt.UserRole, row)
            self.table.setItem(row, 0, miller_item)

            # Use numeric sort items for columns that should sort numerically
            shift_item = QTableWidgetItem()
            shift_item.setData(Qt.DisplayRole, float(round(r["shift"], 4)))
            self.table.setItem(row, 1, shift_item)

            atoms_item = QTableWidgetItem()
            atoms_item.setData(Qt.DisplayRole, int(r["num_atoms"]))
            self.table.setItem(row, 2, atoms_item)

            area_item = QTableWidgetItem()
            area_item.setData(Qt.DisplayRole, float(round(r["surface_area"], 2)))
            self.table.setItem(row, 3, area_item)

            sym_text = "Yes" if r["is_symmetric"] else ("No" if r["is_symmetric"] is not None else "N/A")
            sym_item = QTableWidgetItem(sym_text)
            if r["is_symmetric"] is True:
                sym_item.setBackground(QColor(200, 255, 200))
                sym_item.setForeground(QColor(0, 80, 0))
            elif r["is_symmetric"] is False:
                sym_item.setBackground(QColor(255, 255, 200))
                sym_item.setForeground(QColor(120, 100, 0))
            self.table.setItem(row, 4, sym_item)

            self.table.setItem(row, 5, QTableWidgetItem(r["formula"]))

        self.table.setSortingEnabled(True)

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Screening Results", "screening_results.csv",
            "CSV files (*.csv);;All Files (*)"
        )
        if not path:
            return

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Miller Index", "Shift", "Atoms",
                "Surface Area (A^2)", "Symmetric", "Formula"
            ])
            for r in self.results:
                writer.writerow([
                    r["miller_str"], r["shift"], r["num_atoms"],
                    r["surface_area"], r["is_symmetric"], r["formula"]
                ])

        QMessageBox.information(self, "Exported", f"Results saved to:\n{path}")

    def _export_all_poscar(self):
        """Export all screening results as POSCAR files (Feature #19)."""
        if not self.results:
            return

        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory for POSCAR Files")
        if not output_dir:
            return

        exported = []
        for r in self.results:
            h, k, l = r["miller"]
            shift = r["shift"]
            fname = f"POSCAR_{h}-{k}-{l}_shift{shift}.vasp".replace(".", "-") + ""
            # Clean up double extensions from replace
            fname = f"POSCAR_{h}{k}{l}_shift{str(shift).replace('.', '-')}.vasp"
            fpath = os.path.join(output_dir, fname)
            Poscar(r["slab"]).write_file(fpath)
            exported.append(fname)

        QMessageBox.information(
            self, "Export Complete",
            f"Exported {len(exported)} POSCAR files to:\n{output_dir}")

    def _get_original_index(self, visual_row):
        """Map a visual table row back to the original results list index."""
        item = self.table.item(visual_row, 0)
        if item is None:
            return -1
        return item.data(Qt.UserRole)

    def _load_selected(self):
        visual_row = self.table.currentRow()
        if visual_row < 0:
            QMessageBox.warning(self, "Error", "No surface selected.")
            return
        orig_idx = self._get_original_index(visual_row)
        if orig_idx < 0 or orig_idx >= len(self.results):
            QMessageBox.warning(self, "Error", "No surface selected.")
            return
        r = self.results[orig_idx]
        self.load_surface.emit(r["slab"], r["miller"])
        self.close()
