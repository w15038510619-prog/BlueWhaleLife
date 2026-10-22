import sys
import os
import time
import threading
import webbrowser
import uvicorn
from PySide6.QtWidgets import QApplication
from backend.app.main import app as fastapi_app
from desktop_pet.pet_window import PetWindow


def run_api_server():
    """Run uvicorn in a background thread"""
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="warning")


def main():
    # 1. Start backend API & Web Server in background thread
    server_thread = threading.Thread(target=run_api_server, daemon=True)
    server_thread.start()

    # 2. Automatically open web dashboard after a brief delay
    def _open_browser():
        time.sleep(1.8)
        webbrowser.open("http://127.0.0.1:8000")

    browser_thread = threading.Thread(target=_open_browser, daemon=True)
    browser_thread.start()

    # 3. Start PySide6 Desktop Pet (Shark Musume) in main UI thread
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("BlueWhaleLife - 大肥鱼·鲨鱼娘")
    qt_app.setQuitOnLastWindowClosed(False)

    pet = PetWindow(backend_url="http://127.0.0.1:8000")
    pet.show()

    # When desktop pet window exits, exit the entire app
    exit_code = qt_app.exec()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
