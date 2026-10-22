from __future__ import annotations
from typing import Optional, Callable
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QPainterPath, QBrush, QPen, QFont
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout


class SpeechBubble(QWidget):
    """
    Cute semi-transparent floating bubble displaying 大肥鱼's current thoughts,
    discoveries, or interactive confirmations (such as trash recycling).
    """

    def __init__(self, parent=None, on_chat_clicked=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(260)

        self.on_chat_clicked = on_chat_clicked
        self._on_confirm_cb: Optional[Callable] = None
        self._on_cancel_cb: Optional[Callable] = None

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 12, 14, 16)
        self.layout.setSpacing(8)

        self.mood_label = QLabel("✨ 模拟心境：探索兴起", self)
        self.mood_label.setStyleSheet("color: #2b6cb0; font-weight: bold; font-size: 11px;")
        self.layout.addWidget(self.mood_label)

        self.text_label = QLabel("今天有什么好玩的知识在等着我们呢？咕噜噜~", self)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet("color: #1a202c; font-size: 12px; line-height: 1.4;")
        self.layout.addWidget(self.text_label)

        # Standard Chat Button Row
        self.chat_btn_row = QHBoxLayout()
        self.chat_btn_row.addStretch()

        self.chat_btn = QPushButton("💬 找我聊天", self)
        self.chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chat_btn.setStyleSheet("""
            QPushButton {
                background: #3182ce;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2b6cb0;
            }
        """)
        if self.on_chat_clicked:
            self.chat_btn.clicked.connect(self.on_chat_clicked)
        self.chat_btn_row.addWidget(self.chat_btn)
        self.layout.addLayout(self.chat_btn_row)

        # Recycle Confirmation Button Row (Initially hidden)
        self.confirm_btn_row = QHBoxLayout()
        self.confirm_btn_row.setSpacing(8)

        self.cancel_btn = QPushButton("留着吧", self)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #e2e8f0;
                color: #475569;
                border: none;
                border-radius: 8px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #cbd5e1;
            }
        """)
        self.cancel_btn.clicked.connect(self._handle_cancel_clicked)
        self.confirm_btn_row.addWidget(self.cancel_btn)

        self.confirm_btn = QPushButton("🗑️ 送去回收站", self)
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background: #ef4444;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #dc2626;
            }
        """)
        self.confirm_btn.clicked.connect(self._handle_confirm_clicked)
        self.confirm_btn_row.addWidget(self.confirm_btn)

        self.layout.addLayout(self.confirm_btn_row)
        self._set_confirm_mode(False)

        self.auto_hide_timer = QTimer(self)
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self.hide)

    def _set_confirm_mode(self, enabled: bool):
        for i in range(self.chat_btn_row.count()):
            w = self.chat_btn_row.itemAt(i).widget()
            if w:
                w.setVisible(not enabled)
        for i in range(self.confirm_btn_row.count()):
            w = self.confirm_btn_row.itemAt(i).widget()
            if w:
                w.setVisible(enabled)

    def _handle_confirm_clicked(self):
        self.hide()
        if self._on_confirm_cb:
            self._on_confirm_cb()

    def _handle_cancel_clicked(self):
        self.hide()
        if self._on_cancel_cb:
            self._on_cancel_cb()

    def show_message(self, mood: str, text: str, duration_ms: int = 6000):
        self._set_confirm_mode(False)
        self.mood_label.setText(f"✨ 模拟心境：{mood}")
        self.text_label.setText(text)
        self.adjustSize()
        self.show()
        if duration_ms > 0:
            self.auto_hide_timer.start(duration_ms)

    def show_recycle_confirm(
        self,
        file_name: str,
        size_str: str,
        on_confirm: Callable,
        on_cancel: Callable
    ):
        """Display an interactive modal prompt asking to confirm moving file to Recycle Bin."""
        self.auto_hide_timer.stop()
        self._on_confirm_cb = on_confirm
        self._on_cancel_cb = on_cancel

        self._set_confirm_mode(True)
        self.mood_label.setText("🗑️ 发现待处理垃圾")
        self.text_label.setText(f"主人，要把这个文件送进 Windows 回收站吗？\n📄 <b>{file_name}</b> ({size_str})")
        self.adjustSize()
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        path = QPainterPath()
        rect = QRectF(2, 2, w - 4, h - 10)
        path.addRoundedRect(rect, 12, 12)

        # Draw tail
        path.moveTo(w / 2 - 8, h - 10)
        path.lineTo(w / 2, h - 2)
        path.lineTo(w / 2 + 8, h - 10)

        # Fill background
        painter.setPen(QPen(QColor(200, 225, 255, 220), 1.5))
        painter.setBrush(QBrush(QColor(255, 255, 255, 250)))
        painter.drawPath(path)
