import os
import sys
import tempfile
import time
from pathlib import Path

# Ensure repo root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QPoint
from PySide6.QtGui import QPixmap

from desktop_pet.pet_window import PetWindow
from desktop_pet.recycle_bin_helper import is_safe_to_recycle, recycle_file


def run_visual_and_trash_test():
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)

    pet = PetWindow(backend_url="http://127.0.0.1:8000")
    pet.show()

    output_dir = Path("desktop_pet/assets/test_renders")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=== Testing Whale Musume Desktop Pet Visuals & Trash Mission ===")

    # 1. Capture idle state
    app.processEvents()
    time.sleep(0.1)
    pix = pet.renderer.grab()
    pix.save(str(output_dir / "test_pet_idle.png"))
    print("Saved test_pet_idle.png")

    # 2. Test Headpat
    pet.renderer.set_state("headpat")
    app.processEvents()
    time.sleep(0.1)
    pix = pet.renderer.grab()
    pix.save(str(output_dir / "test_pet_headpat.png"))
    print("Saved test_pet_headpat.png")

    # 3. Test Feed
    pet.renderer.set_state("feed")
    app.processEvents()
    time.sleep(0.1)
    pix = pet.renderer.grab()
    pix.save(str(output_dir / "test_pet_feed.png"))
    print("Saved test_pet_feed.png")

    # 4. Test Thinking
    pet.renderer.set_state("thinking")
    app.processEvents()
    time.sleep(0.1)
    pix = pet.renderer.grab()
    pix.save(str(output_dir / "test_pet_thinking.png"))
    print("Saved test_pet_thinking.png")

    # 5. Test Celebrate
    pet.renderer.set_state("celebrate")
    app.processEvents()
    time.sleep(0.1)
    pix = pet.renderer.grab()
    pix.save(str(output_dir / "test_pet_celebrate.png"))
    print("Saved test_pet_celebrate.png")

    # 6. Test File Trash Mission
    with tempfile.NamedTemporaryFile(delete=False, prefix="whale_recycle_test_", suffix=".txt") as tf:
        tf.write(b"Hello from Whale Musume recycle bin test!")
        tmp_file = tf.name

    print(f"Created test temporary file: {tmp_file}")
    assert os.path.exists(tmp_file)

    # Test safe check
    safe, reason = is_safe_to_recycle(tmp_file)
    print(f"Is temporary file safe to recycle? {safe}")
    assert safe is True

    # Trigger dropped file handler
    pet._handle_file_dropped(tmp_file)
    app.processEvents()

    # Capture confirmation state
    pix_confirm = pet.grab()
    pix_confirm.save(str(output_dir / "test_pet_file_confirm.png"))
    print("Saved test_pet_file_confirm.png")

    # Start mission
    pet._start_recycle_mission(tmp_file)
    app.processEvents()
    time.sleep(0.1)

    # Capture carrying file while running
    pix_running = pet.grab()
    pix_running.save(str(output_dir / "test_pet_running_file.png"))
    print("Saved test_pet_running_file.png")

    # Simulate steps
    for _ in range(35):
        pet._on_move_tick()
        app.processEvents()
        time.sleep(0.01)

    # Trigger arrival & throwing
    pet._on_arrived_at_bin()
    app.processEvents()
    time.sleep(0.1)
    pix_throw = pet.grab()
    pix_throw.save(str(output_dir / "test_pet_throwing.png"))
    print("Saved test_pet_throwing.png")

    # Wait for delete callback
    for _ in range(30):
        app.processEvents()
        time.sleep(0.03)

    print("Verifying file status...")
    file_still_exists = os.path.exists(tmp_file)
    print(f"File exists on disk after recycling? {file_still_exists}")
    assert not file_still_exists, "File should have been safely moved to Windows Recycle Bin!"

    # Simulate return home steps
    pet._start_return_home()
    for _ in range(40):
        pet._on_move_tick()
        app.processEvents()
        time.sleep(0.01)

    pet._on_returned_home()
    app.processEvents()
    time.sleep(0.1)

    print("Visual and Trash Mission Test SUCCESSFUL!")
    pet.close()


if __name__ == "__main__":
    run_visual_and_trash_test()
