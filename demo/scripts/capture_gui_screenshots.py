"""
Script to automate GUI interactions and capture screenshots at each step.
"""
import sys
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap, QScreen

# Create output directory (relative to script location)
script_dir = Path(__file__).parent
screenshot_dir = script_dir.parent / "output" / "gui_screenshots"
screenshot_dir.mkdir(parents=True, exist_ok=True)

# Add project root to path
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

from ui.main_window import MainWindow

app = QApplication(sys.argv)
window = MainWindow()
window.show()

# Wait for window to be fully rendered
QApplication.processEvents()
time.sleep(1)

screenshots = []

def take_screenshot(name, description):
    """Capture a screenshot of the main window."""
    pixmap = window.grab()
    filepath = screenshot_dir / f"{name}.png"
    pixmap.save(str(filepath))
    screenshots.append((name, description, filepath))
    print(f"Captured: {name} - {description}")
    QApplication.processEvents()
    time.sleep(0.5)  # Brief pause between screenshots

def step1_initial_state():
    """Step 1: Initial application state"""
    take_screenshot("01_initial_state", "Application startup - empty state")

def step2_search():
    """Step 2: Enter search query"""
    window.formula_input.setText("TiO2")
    QApplication.processEvents()
    time.sleep(0.3)
    take_screenshot("02_search_entered", "Search query entered: TiO2")

def step3_search_clicked():
    """Step 3: Click search button"""
    window.search_button.click()
    QApplication.processEvents()
    time.sleep(0.5)
    take_screenshot("03_searching", "Search in progress")

def step4_results_displayed():
    """Step 4: Wait for results and capture"""
    # Wait for search to complete (check if table has rows)
    max_wait = 30
    waited = 0
    while window.struct_table.rowCount() == 0 and waited < max_wait:
        QApplication.processEvents()
        time.sleep(0.5)
        waited += 0.5
    
    if window.struct_table.rowCount() > 0:
        take_screenshot("04_search_results", "Search results displayed in table")
    else:
        print("Warning: Search results not found, using demo structure")
        # Load a demo structure instead
        from pymatgen.core import Structure, Lattice
        lattice = Lattice.tetragonal(4.6, 2.96)
        species = ["Ti", "Ti", "O", "O", "O", "O"]
        coords = [
            [0.0, 0.0, 0.0],
            [0.5, 0.5, 0.5],
            [0.3, 0.3, 0.0],
            [0.7, 0.7, 0.0],
            [0.2, 0.8, 0.5],
            [0.8, 0.2, 0.5],
        ]
        structure = Structure(lattice, species, coords)
        window.local_structure = structure
        window.structure_viewer.update_structure(structure)
        window.filename_line.setText("demo_TiO2.vasp")
        QApplication.processEvents()
        time.sleep(0.5)
        take_screenshot("04_demo_structure_loaded", "Demo structure loaded (MP API unavailable)")

def step5_select_structure():
    """Step 5: Select a structure from results"""
    if window.struct_table.rowCount() > 0:
        window.struct_table.selectRow(0)
        window.struct_table.setCurrentCell(0, 0)
        QApplication.processEvents()
        time.sleep(1)  # Wait for viewer to update
        take_screenshot("05_structure_selected", "Structure selected - 3D viewer updated")
    else:
        # Already have demo structure loaded
        take_screenshot("05_structure_selected", "Demo structure displayed in 3D viewer")

def step6_set_slab_params():
    """Step 6: Configure slab generation parameters"""
    window.h_spin.setValue(1)
    window.k_spin.setValue(0)
    window.l_spin.setValue(1)
    window.zreps_spin.setValue(3)
    window.vacuum_spin.setValue(15.0)
    window.all_terminations_check.setChecked(True)
    QApplication.processEvents()
    time.sleep(0.3)
    take_screenshot("06_slab_params_set", "Slab parameters configured: (1,0,1), z_reps=3, vacuum=15Å")

def step7_generate_slabs():
    """Step 7: Generate slabs"""
    window.generate_slabs_button.click()
    QApplication.processEvents()
    time.sleep(0.5)
    take_screenshot("07_generating_slabs", "Slab generation in progress")

def step8_slabs_generated():
    """Step 8: Wait for slabs to be generated"""
    max_wait = 30
    waited = 0
    while len(window.generated_slabs) == 0 and waited < max_wait:
        QApplication.processEvents()
        time.sleep(0.5)
        waited += 0.5
    
    if len(window.generated_slabs) > 0:
        QApplication.processEvents()
        time.sleep(0.5)
        take_screenshot("08_slabs_generated", "Slabs generated and displayed in table")
    else:
        print("Warning: Slab generation may have failed")

def step9_slab_selected():
    """Step 9: Select a slab and show properties"""
    if window.slabs_table.rowCount() > 0:
        window.slabs_table.selectRow(0)
        window.slabs_table.setCurrentCell(0, 0)
        QApplication.processEvents()
        time.sleep(1)  # Wait for viewer and info panel to update
        take_screenshot("09_slab_selected", "Slab selected - 3D viewer and properties panel updated")

def step10_open_screening():
    """Step 10: Open surface screening dialog"""
    window.screen_button.click()
    QApplication.processEvents()
    time.sleep(0.5)
    
    # Find the screening dialog
    from PySide6.QtWidgets import QDialog
    dialog = None
    for widget in QApplication.allWidgets():
        if isinstance(widget, QDialog) and widget.isVisible():
            dialog = widget
            break
    
    if dialog:
        pixmap = dialog.grab()
        filepath = screenshot_dir / "10_screening_dialog.png"
        pixmap.save(str(filepath))
        screenshots.append(("10_screening_dialog", "Surface screening dialog opened", filepath))
        print(f"Captured: 10_screening_dialog - Surface screening dialog opened")
        QApplication.processEvents()
        time.sleep(0.5)

def step11_close_screening():
    """Step 11: Close screening dialog and return to main window"""
    from PySide6.QtWidgets import QDialog
    for widget in QApplication.allWidgets():
        if isinstance(widget, QDialog) and widget.isVisible():
            widget.close()
            break
    QApplication.processEvents()
    time.sleep(0.5)

def step12_open_dft_dialog():
    """Step 12: Open DFT input dialog"""
    if window.slabs_table.rowCount() > 0:
        window.dft_button.click()
        QApplication.processEvents()
        time.sleep(0.5)
        
        # Find the DFT dialog
        from PySide6.QtWidgets import QDialog
        dialog = None
        for widget in QApplication.allWidgets():
            if isinstance(widget, QDialog) and widget.isVisible():
                dialog = widget
                break
        
        if dialog:
            pixmap = dialog.grab()
            filepath = screenshot_dir / "11_dft_dialog.png"
            pixmap.save(str(filepath))
            screenshots.append(("11_dft_dialog", "DFT input generation dialog", filepath))
            print(f"Captured: 11_dft_dialog - DFT input generation dialog")
            QApplication.processEvents()
            time.sleep(0.5)

def step13_close_dft():
    """Step 13: Close DFT dialog"""
    from PySide6.QtWidgets import QDialog
    for widget in QApplication.allWidgets():
        if isinstance(widget, QDialog) and widget.isVisible():
            widget.close()
            break
    QApplication.processEvents()
    time.sleep(0.5)

def step14_final_state():
    """Step 14: Final state with all features demonstrated"""
    take_screenshot("12_final_state", "Final state - all features demonstrated")

def run_capture_sequence():
    """Run the complete screenshot capture sequence"""
    print("Starting GUI screenshot capture sequence...")
    print("=" * 60)
    
    try:
        step1_initial_state()
        step2_search()
        step3_search_clicked()
        step4_results_displayed()
        step5_select_structure()
        step6_set_slab_params()
        step7_generate_slabs()
        step8_slabs_generated()
        step9_slab_selected()
        step10_open_screening()
        step11_close_screening()
        step12_open_dft_dialog()
        step13_close_dft()
        step14_final_state()
        
        print("=" * 60)
        print(f"\nScreenshot capture complete!")
        print(f"Captured {len(screenshots)} screenshots in: {screenshot_dir}")
        print("\nScreenshots captured:")
        for name, desc, path in screenshots:
            print(f"  - {name}: {desc}")
        
    except Exception as e:
        print(f"Error during capture: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close application
        QTimer.singleShot(1000, app.quit)

# Schedule the capture sequence
QTimer.singleShot(2000, run_capture_sequence)  # Start after 2 seconds

# Run the application
sys.exit(app.exec())
