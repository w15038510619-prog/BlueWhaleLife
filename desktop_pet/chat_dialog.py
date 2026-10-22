from __future__ import annotations
import threading
import httpx
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel


class ChatWorker(QObject):
    response_ready = Signal(str, str)
    error_occurred = Signal(str)

    def send_message(self, message: str, backend_url: str):
        def _run():
            try:
                res = httpx.post(
                    f"{backend_url}/api/pet/chat",
                    json={"message": message},
                    timeout=30.0
                )
                if res.status_code == 200:
                    data = res.json()
                    self.response_ready.emit(data.get("reply", ""), data.get("pet_state", "happy"))
                else:
                    self.error_occurred.emit(f"服务端响应错误: {res.status_code}")
            except Exception as e:
                # Standalone fallback if backend is offline
                fallback_reply = f"咕噜噜~ 我收到你的话啦：“{message}”！虽然我的主脑服务好像暂时没连接上，但我依然在这里陪着你！"
                self.response_ready.emit(fallback_reply, "happy")

        threading.Thread(target=_run, daemon=True).start()


class ChatDialog(QDialog):
    """
    Modern mini chat window for talking with 大肥鱼 directly from the desktop.
    """

    def __init__(self, backend_url="http://127.0.0.1:8000", parent=None, on_state_change=None):
        super().__init__(parent)
        self.backend_url = backend_url
        self.on_state_change = on_state_change

        self.setWindowTitle("与大肥鱼聊天")
        self.setFixedSize(360, 420)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet("""
            QDialog {
                background: #f7fafc;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Microsoft YaHei", sans-serif;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header
        header = QLabel("🐟 正在与大肥鱼畅所欲言", self)
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #2b6cb0;")
        layout.addWidget(header)

        # Chat history display
        self.history_box = QTextEdit(self)
        self.history_box.setReadOnly(True)
        self.history_box.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
                line-height: 1.5;
            }
        """)
        self.history_box.append("<b style='color: #3182ce;'>大肥鱼：</b> 咕噜噜~ 主人今天遇到什么好玩的事情了吗？随时跟我聊聊！<br>")
        layout.addWidget(self.history_box)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.input_edit = QLineEdit(self)
        self.input_edit.setPlaceholderText("给大肥鱼发消息...")
        self.input_edit.setStyleSheet("""
            QLineEdit {
                background: white;
                border: 1px solid #cbd5e0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #3182ce;
            }
        """)
        self.input_edit.returnPressed.connect(self._handle_send)
        input_row.addWidget(self.input_edit)

        self.send_btn = QPushButton("发送", self)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: #3182ce;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #2b6cb0;
            }
            QPushButton:disabled {
                background: #a0aec0;
            }
        """)
        self.send_btn.clicked.connect(self._handle_send)
        input_row.addWidget(self.send_btn)

        layout.addLayout(input_row)

        # Worker setup
        self.worker = ChatWorker()
        self.worker.response_ready.connect(self._on_response)
        self.worker.error_occurred.connect(self._on_error)

    def _handle_send(self):
        msg = self.input_edit.text().strip()
        if not msg:
            return

        self.history_box.append(f"<b style='color: #4a5568;'>主人：</b> {msg}")
        self.input_edit.clear()
        self.send_btn.setEnabled(False)
        self.input_edit.setEnabled(False)

        if self.on_state_change:
            self.on_state_change("thinking")

        self.worker.send_message(msg, self.backend_url)

    def _on_response(self, reply: str, state: str):
        self.history_box.append(f"<b style='color: #3182ce;'>大肥鱼：</b> {reply}<br>")
        self.send_btn.setEnabled(True)
        self.input_edit.setEnabled(True)
        self.input_edit.setFocus()

        if self.on_state_change:
            self.on_state_change(state)

    def _on_error(self, err: str):
        self.history_box.append(f"<span style='color: #e53e3e;'>[提示]: {err}</span><br>")
        self.send_btn.setEnabled(True)
        self.input_edit.setEnabled(True)
