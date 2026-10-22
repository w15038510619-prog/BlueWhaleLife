import sys
import os
import time
import threading
import urllib.request
import webbrowser
import uvicorn
from PySide6.QtWidgets import QApplication

# 1. Windows No-Console Mode Stdout/Stderr Guard
# Prevents uvicorn and click from crashing with AttributeError: 'NoneType' object has no attribute 'isatty'
class SafeStream:
    def write(self, s):
        pass
    def flush(self):
        pass
    def isatty(self):
        return False

if sys.stdout is None:
    sys.stdout = SafeStream()
if sys.stderr is None:
    sys.stderr = SafeStream()

from backend.app.main import app as fastapi_app
from desktop_pet.pet_window import PetWindow


def run_api_server():
    """Run uvicorn in a background daemon thread with safe log config"""
    try:
        uvicorn.run(
            fastapi_app,
            host="127.0.0.1",
            port=8000,
            log_config=None,
            access_log=False
        )
    except Exception as e:
        with open("server_error.log", "w", encoding="utf-8") as f:
            f.write(f"Server startup exception: {e}\n")


def wait_and_open_browser():
    """Waits until the backend server is actually responding before opening browser"""
    for _ in range(30):
        try:
            req = urllib.request.Request("http://127.0.0.1:8000/api/health")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    webbrowser.open("http://127.0.0.1:8000")
                    return
        except Exception:
            pass
        time.sleep(0.3)
    # Fallback open if wait loop times out
    webbrowser.open("http://127.0.0.1:8000")


def main():
    # 1. Start backend API & Web Server in background thread
    server_thread = threading.Thread(target=run_api_server, daemon=True)
    server_thread.start()

    # 2. Wait for server to be responsive, then open browser
    browser_thread = threading.Thread(target=wait_and_open_browser, daemon=True)
    browser_thread.start()

    # 3. Start PySide6 Desktop Pet (Whale Musume / 鲸鱼娘) in main UI thread
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("BlueWhaleLife - 大肥鱼·鲸鱼娘")
    qt_app.setQuitOnLastWindowClosed(False)

    pet = PetWindow(backend_url="http://127.0.0.1:8000")
    pet.show()

    # When desktop pet window exits, exit the entire app
    exit_code = qt_app.exec()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
