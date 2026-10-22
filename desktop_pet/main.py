import sys
import os
from PySide6.QtWidgets import QApplication
from desktop_pet.pet_window import PetWindow


def main():
    # Windows high DPI scaling support
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    app.setApplicationName("BlueWhaleLife - 大肥鱼桌宠")
    app.setQuitOnLastWindowClosed(False)

    window = PetWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
