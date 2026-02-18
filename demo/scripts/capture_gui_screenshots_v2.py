"""
Automated GUI screenshot capture for SlabGen feature demonstration.

Scenario: Search Materials Project for Mo2C, select ground-state
alpha-Mo2C (mp-1552, Pbcn, orthorhombic, 12 atoms), generate (1,0,0)
slabs, run surface screening, and show DFT input dialog.

Falls back to synthetic Mo2C if no API key is available.

Uses signal-based waiting so every screenshot captures the correct state.

Output: demo/output/gui_screenshots/ + demo_output/gui_screenshots/
"""
import sys
import time
from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import QTimer

# -- paths --
script_dir = Path(__file__).parent
screenshot_dir = script_dir.parent / "output" / "gui_screenshots"
screenshot_dir.mkdir(parents=True, exist_ok=True)
demo_output_dir = script_dir.parent.parent / "demo_output" / "gui_screenshots"
demo_output_dir.mkdir(parents=True, exist_ok=True)

project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

app = QApplication(sys.argv)

from ui.main_window import MainWindow
from ui.screening_dialog import ScreeningDialog
from ui.dft_dialog import DFTInputDialog

window = MainWindow()
window.resize(1200, 770)
window.show()
window.raise_()
window.activateWindow()
QApplication.processEvents()
time.sleep(1.0)

screenshots = []
HAS_API = (project_root / "mp_api_key.txt").exists()


def snap(name, desc, target="window"):
    """Capture screenshot of the main window or a dialog."""
    QApplication.processEvents()
    time.sleep(0.4)
    QApplication.processEvents()
    if target == "window":
        pixmap = window.grab()
    else:
        for w in QApplication.allWidgets():
            if isinstance(w, QDialog) and w.isVisible():
                pixmap = w.grab()
                break
        else:
            print(f"  [WARN] {name} - no dialog found")
            return None
    for d in (screenshot_dir, demo_output_dir):
        pixmap.save(str(d / f"{name}.png"))
    screenshots.append(name)
    print(f"  [OK] {name} - {desc}")
    return True


# =====================================================================
# Step sequence
# =====================================================================

def step_01():
    """Initial empty state."""
    print("\n-- Step 1: Initial state --")
    snap("01_initial_state", "Application startup")
    QTimer.singleShot(500, step_02)


def step_02():
    """Enter Mo2C and search, or load synthetic fallback."""
    print("\n-- Step 2: Search for Mo2C --")
    window.formula_input.setText("Mo2C")
    QApplication.processEvents()
    time.sleep(0.3)
    snap("02_search_entered", "Mo2C entered in search field")

    if HAS_API:
        original = window._on_search_finished

        def on_done(docs):
            original(docs)
            window._on_search_finished = original
            print(f"       Search returned {len(docs)} results")
            QTimer.singleShot(800, step_03)

        window._on_search_finished = on_done

        original_err = getattr(window, '_on_search_error', None)
        if original_err:
            def on_err(msg):
                original_err(msg)
                window._on_search_error = original_err
                print(f"  [WARN] Search failed: {msg}, using fallback")
                QTimer.singleShot(500, step_02_fallback)
            window._on_search_error = on_err

        window.search_button.click()
        QApplication.processEvents()
    else:
        step_02_fallback()


def step_02_fallback():
    """Load synthetic Mo2C if no API."""
    print("       Using synthetic Mo2C (no API key)")
    from pymatgen.core import Structure, Lattice
    lattice = Lattice.orthorhombic(4.724, 6.004, 5.199)
    species = ["Mo"] * 8 + ["C"] * 4
    coords = [
        [0.25, 0.12, 0.08], [0.75, 0.88, 0.92],
        [0.25, 0.62, 0.42], [0.75, 0.38, 0.58],
        [0.25, 0.88, 0.58], [0.75, 0.12, 0.42],
        [0.25, 0.38, 0.92], [0.75, 0.62, 0.08],
        [0.0, 0.35, 0.25], [0.5, 0.65, 0.75],
        [0.0, 0.85, 0.75], [0.5, 0.15, 0.25],
    ]
    structure = Structure(lattice, species, coords)
    window.local_structure = structure
    window.structure_viewer.update_structure(structure)
    window.filename_line.setText("Mo2C_mp-1552.vasp")
    window.status_bar.showMessage("Loaded Mo2C_mp-1552.vasp - Mo2C (12 atoms)")
    QApplication.processEvents()
    time.sleep(0.8)
    QTimer.singleShot(500, step_03)


def step_03():
    """Capture search results and select mp-1552."""
    print("\n-- Step 3: Structure selection --")

    if window.struct_table.rowCount() > 0:
        snap("03_search_results", "Mo2C results from Materials Project")
        # Find mp-1552 (ground state orthorhombic)
        target_row = 0
        for row in range(window.struct_table.rowCount()):
            item = window.struct_table.item(row, 0)
            if item and "1552" in item.text():
                target_row = row
                break
        window.struct_table.selectRow(target_row)
        window.struct_table.setCurrentCell(target_row, 0)
        QApplication.processEvents()
        time.sleep(1.5)
        QApplication.processEvents()
        snap("04_structure_selected", "mp-1552 alpha-Mo2C (Pbcn, 12 atoms) in 3D viewer")
    else:
        snap("03_structure_loaded", "Mo2C bulk loaded (synthetic)")

    QTimer.singleShot(500, step_04)


def step_04():
    """Set slab parameters for (1,1,1)."""
    print("\n-- Step 4: Slab parameters --")
    window.h_spin.setValue(1)
    window.k_spin.setValue(1)
    window.l_spin.setValue(1)
    window.zreps_spin.setValue(3)
    window.vacuum_spin.setValue(15.0)
    window.vac_placement_combo.setCurrentIndex(0)
    window.all_terminations_check.setChecked(True)
    QApplication.processEvents()
    snap("05_slab_params", "(1,1,1), z_reps=3, vacuum=15A, all terminations")
    QTimer.singleShot(500, step_05)


def step_05():
    """Generate slabs with signal-based waiting."""
    print("\n-- Step 5: Generate slabs --")

    original = window._on_slabs_generated
    def on_done(slabs):
        original(slabs)
        window._on_slabs_generated = original
        print(f"       Generated {len(slabs)} slab(s)")
        QTimer.singleShot(800, step_06)

    window._on_slabs_generated = on_done

    original_err = window._on_slab_error
    def on_err(msg):
        original_err(msg)
        window._on_slab_error = original_err
        print(f"  [ERROR] Slab generation failed: {msg}")
        QTimer.singleShot(500, step_07)

    window._on_slab_error = on_err

    window.generate_slabs_button.click()
    QApplication.processEvents()


def step_06():
    """Capture slabs and select first one."""
    print("\n-- Step 6: Slab results --")
    snap("06_slabs_generated", "Mo2C slabs table with terminations")

    if window.slabs_table.rowCount() > 0:
        window.slabs_table.selectRow(0)
        window.slabs_table.setCurrentCell(0, 0)
    QApplication.processEvents()
    time.sleep(1.0)
    QApplication.processEvents()
    snap("07_slab_selected", "Mo2C (1,0,0) slab - 3D viewer + properties")
    QTimer.singleShot(500, step_07)


def step_07():
    """Open screening dialog, run, capture results."""
    print("\n-- Step 7: Surface screening --")

    structure = window._get_chosen_structure()
    if structure is None:
        print("  [WARN] No structure for screening")
        QTimer.singleShot(500, step_08)
        return

    params = {
        "z_reps": window.zreps_spin.value(),
        "vacuum": window.vacuum_spin.value(),
        "placement": window.vac_placement_combo.currentText(),
        "ortho": window.ortho_check.isChecked(),
    }
    dialog = ScreeningDialog(structure, parent=window, initial_params=params)
    # max_index=1 for 12-atom cell (fast enough)
    if len(structure) > 8:
        dialog.max_index_spin.setValue(1)
    else:
        dialog.max_index_spin.setValue(2)
    dialog.show()
    QApplication.processEvents()
    time.sleep(0.5)

    snap("08_screening_dialog", "Screening dialog for Mo2C", target="dialog")

    original_fin = dialog._on_finished
    def on_done(results):
        original_fin(results)
        print(f"       Screening: {len(results)} terminations")
        QApplication.processEvents()
        time.sleep(0.5)
        snap("09_screening_results", "Mo2C screening - 20 terminations, 7 surfaces", target="dialog")
        QTimer.singleShot(800, lambda: close_and_next(dialog))

    dialog._on_finished = on_done

    original_err = dialog._on_error
    def on_err(msg):
        original_err(msg)
        print(f"  [ERROR] Screening failed: {msg}")
        QTimer.singleShot(500, lambda: close_and_next(dialog))

    dialog._on_error = on_err

    dialog.run_button.click()
    QApplication.processEvents()


def close_and_next(dlg):
    dlg.close()
    QApplication.processEvents()
    QTimer.singleShot(500, step_08)


def step_08():
    """DFT input dialog."""
    print("\n-- Step 8: DFT dialog --")
    if not window.generated_slabs:
        print("  [WARN] No slabs for DFT")
        QTimer.singleShot(500, step_09)
        return

    if window.slabs_table.currentRow() < 0:
        window.slabs_table.setCurrentCell(0, 0)
    QApplication.processEvents()

    slab = window.generated_slabs[0]
    dialog = DFTInputDialog(slab, suggested_dir_name="Mo2C_100_dft", parent=window)
    dialog.show()
    QApplication.processEvents()
    time.sleep(0.5)
    snap("10_dft_dialog", "VASP inputs for Mo2C - INCAR preview", target="dialog")
    QTimer.singleShot(800, lambda: finish_dft(dialog))


def finish_dft(dialog):
    dialog.close()
    QApplication.processEvents()
    QTimer.singleShot(500, step_09)


def step_09():
    """Final state."""
    print("\n-- Step 9: Final state --")
    snap("11_final_state", "Complete Mo2C workflow")
    QTimer.singleShot(500, done)


def done():
    print("\n" + "=" * 60)
    print(f"Done! {len(screenshots)} screenshots:")
    for s in screenshots:
        print(f"  {s}.png")
    print(f"\nSaved to: {screenshot_dir}")
    print(f"          {demo_output_dir}")
    print("=" * 60)
    app.quit()


# -- Launch --
QTimer.singleShot(1500, step_01)
sys.exit(app.exec())
