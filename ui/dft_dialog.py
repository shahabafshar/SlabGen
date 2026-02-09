import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox,
    QPushButton, QTextEdit, QGroupBox, QFileDialog, QMessageBox,
)

from core.dft_inputs import DFTInputGenerator


class DFTInputDialog(QDialog):
    """Dialog for configuring and generating VASP DFT input files."""

    def __init__(self, slab, suggested_dir_name="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Prepare DFT Inputs")
        self.setMinimumSize(650, 550)
        self.slab = slab
        self.suggested_dir_name = suggested_dir_name
        self.generator = DFTInputGenerator(slab)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # ── Calculation Settings ──
        settings_group = QGroupBox("VASP Calculation Settings")
        settings_layout = QVBoxLayout()

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("ENCUT (eV):"))
        self.encut_spin = QSpinBox()
        self.encut_spin.setRange(200, 1000)
        self.encut_spin.setValue(400)
        self.encut_spin.setSingleStep(50)
        self.encut_spin.valueChanged.connect(self._update_preview)
        row1.addWidget(self.encut_spin)

        row1.addWidget(QLabel("K-point density:"))
        self.kproduct_spin = QSpinBox()
        self.kproduct_spin.setRange(10, 200)
        self.kproduct_spin.setValue(50)
        self.kproduct_spin.valueChanged.connect(self._update_preview)
        row1.addWidget(self.kproduct_spin)

        row1.addWidget(QLabel("ISIF:"))
        self.isif_combo = QComboBox()
        self.isif_combo.addItems([
            "2 — Relax ions only (slab)",
            "3 — Relax ions + cell (bulk)",
        ])
        self.isif_combo.currentIndexChanged.connect(self._update_preview)
        row1.addWidget(self.isif_combo)
        settings_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("ISMEAR:"))
        self.ismear_combo = QComboBox()
        self.ismear_combo.addItems(["0 — Gaussian", "1 — Methfessel-Paxton", "-5 — Tetrahedron"])
        self.ismear_combo.currentIndexChanged.connect(self._update_preview)
        row2.addWidget(self.ismear_combo)

        row2.addWidget(QLabel("SIGMA:"))
        self.sigma_spin = QDoubleSpinBox()
        self.sigma_spin.setRange(0.01, 1.0)
        self.sigma_spin.setValue(0.05)
        self.sigma_spin.setSingleStep(0.01)
        self.sigma_spin.valueChanged.connect(self._update_preview)
        row2.addWidget(self.sigma_spin)

        row2.addWidget(QLabel("EDIFFG:"))
        self.ediffg_spin = QDoubleSpinBox()
        self.ediffg_spin.setRange(-1.0, 0.0)
        self.ediffg_spin.setValue(-0.02)
        self.ediffg_spin.setSingleStep(0.01)
        self.ediffg_spin.setDecimals(3)
        self.ediffg_spin.valueChanged.connect(self._update_preview)
        row2.addWidget(self.ediffg_spin)

        self.dipole_check = QCheckBox("Auto dipole correction")
        self.dipole_check.setChecked(True)
        self.dipole_check.stateChanged.connect(self._update_preview)
        row2.addWidget(self.dipole_check)
        settings_layout.addLayout(row2)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # ── INCAR Preview ──
        preview_group = QGroupBox("INCAR Preview")
        preview_layout = QVBoxLayout()
        self.incar_preview = QTextEdit()
        self.incar_preview.setReadOnly(True)
        self.incar_preview.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        preview_layout.addWidget(self.incar_preview)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # ── Action Buttons ──
        action_layout = QHBoxLayout()

        self.generate_button = QPushButton("Generate DFT Inputs")
        self.generate_button.clicked.connect(self._generate)
        action_layout.addWidget(self.generate_button)

        close_button = QPushButton("Cancel")
        close_button.clicked.connect(self.close)
        action_layout.addWidget(close_button)

        layout.addLayout(action_layout)

        # Initial preview
        self._update_preview()

    def _get_config(self):
        """Build config dict from current UI state."""
        isif_map = {0: 2, 1: 3}
        ismear_map = {0: 0, 1: 1, 2: -5}
        return {
            "encut": self.encut_spin.value(),
            "k_product": self.kproduct_spin.value(),
            "isif": isif_map.get(self.isif_combo.currentIndex(), 2),
            "ismear": ismear_map.get(self.ismear_combo.currentIndex(), 0),
            "sigma": self.sigma_spin.value(),
            "ediffg": self.ediffg_spin.value(),
            "auto_dipole": self.dipole_check.isChecked(),
            "is_bulk": (self.isif_combo.currentIndex() == 1),
        }

    def _update_preview(self):
        config = self._get_config()
        preview = self.generator.get_incar_preview(config)
        self.incar_preview.setPlainText(preview)

    def _generate(self):
        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self.suggested_dir_name
        )
        if not output_dir:
            return

        config = self._get_config()
        config["job_name"] = os.path.basename(output_dir) or "slab_relax"

        try:
            paths = self.generator.generate(output_dir, config)
            file_list = "\n".join(f"  {os.path.basename(p)}" for p in paths.values())
            QMessageBox.information(
                self, "DFT Inputs Generated",
                f"Files written to:\n{output_dir}\n\nFiles:\n{file_list}"
            )
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate DFT inputs:\n{str(e)}")
