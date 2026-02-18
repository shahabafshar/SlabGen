"""
Script to capture screening and DFT dialog screenshots.
Assumes a structure is already loaded.
"""
import sys
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import QTimer

# Create output directory (relative to script location)
script_dir = Path(__file__).parent
screenshot_dir = script_dir.parent / "output" / "gui_screenshots"
screenshot_dir.mkdir(parents=True, exist_ok=True)

# Add project root to path
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

app = QApplication(sys.argv)
from ui.main_window import MainWindow

window = MainWindow()
window.show()

# Load a demo structure first
from pymatgen.core import Structure, Lattice
lattice = Lattice.tetragonal(4.6, 2.96)
species = ["Ti", "Ti", "O", "O", "O", "O"]
coords = [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5], [0.3, 0.3, 0.0], 
         [0.7, 0.7, 0.0], [0.2, 0.8, 0.5], [0.8, 0.2, 0.5]]
structure = Structure(lattice, species, coords)
window.local_structure = structure
window.structure_viewer.update_structure(structure)
window.filename_line.setText("demo_TiO2.vasp")

# Generate a slab
window.h_spin.setValue(1)
window.k_spin.setValue(0)
window.l_spin.setValue(1)
window.zreps_spin.setValue(3)
window.vacuum_spin.setValue(15.0)

QApplication.processEvents()
time.sleep(1)

def capture_screening_dialog():
    """Capture screening dialog."""
    window.screen_button.click()
    QApplication.processEvents()
    time.sleep(2)  # Wait for dialog to fully render
    
    for widget in QApplication.allWidgets():
        if isinstance(widget, QDialog) and widget.isVisible():
            pixmap = widget.grab()
            filepath = screenshot_dir / "10_screening_dialog.png"
            pixmap.save(str(filepath))
            print(f"[OK] Captured screening dialog: {filepath.name}")
            QApplication.processEvents()
            time.sleep(1)
            widget.close()
            QApplication.processEvents()
            time.sleep(1)
            return
    
    print("[WARNING] Screening dialog not found")

def capture_dft_dialog():
    """Capture DFT dialog."""
    # First generate a slab
    window.generate_slabs_button.click()
    QApplication.processEvents()
    time.sleep(5)  # Wait for slab generation
    
    if window.slabs_table.rowCount() > 0:
        window.slabs_table.selectRow(0)
        window.dft_button.click()
        QApplication.processEvents()
        time.sleep(2)  # Wait for dialog to fully render
        
        for widget in QApplication.allWidgets():
            if isinstance(widget, QDialog) and widget.isVisible():
                pixmap = widget.grab()
                filepath = screenshot_dir / "11_dft_dialog.png"
                pixmap.save(str(filepath))
                print(f"[OK] Captured DFT dialog: {filepath.name}")
                QApplication.processEvents()
                time.sleep(1)
                widget.close()
                return
        
        print("[WARNING] DFT dialog not found")
    else:
        print("[WARNING] No slabs generated, cannot open DFT dialog")

def finish():
    print("\nDialog capture complete!")
    app.quit()

QTimer.singleShot(2000, capture_screening_dialog)
QTimer.singleShot(8000, capture_dft_dialog)
QTimer.singleShot(12000, finish)

sys.exit(app.exec())
