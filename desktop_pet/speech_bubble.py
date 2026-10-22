from __future__ import annotations
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QPainterPath, QBrush, QPen, QFont
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout


class SpeechBubble(QWidget):
    """
    Cute semi-transparent floating bubble displaying 大肥鱼's current thoughts or discoveries.
    """

    def __init__(self, parent=None, on_chat_clicked=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(240)

        self.on_chat_clicked = on_chat_clicked

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 12, 14, 16)
        self.layout.setSpacing(8)

        self.mood_label = QLabel("✨ 心情：探索兴起", self)
        self.mood_label.setStyleSheet("color: #2b6cb0; font-weight: bold; font-size: 11px;")
        self.layout.addWidget(self.mood_label)

        self.text_label = QLabel("今天有什么好玩的知识在等着我们呢？咕噜噜~", self)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet("color: #1a202c; font-size: 12px; line-height: 1.4;")
        self.layout.addWidget(self.text_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

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
        btn_row.addWidget(self.chat_btn)

        self.layout.addLayout(btn_row)

        self.auto_hide_timer = QTimer(self)
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self.hide)

    def show_message(self, mood: str, text: str, duration_ms: int = 6000):
        self.mood_label.setText(f"✨ 模拟心境：{mood}")
        self.text_label.setText(text)
        self.adjustSize()
        self.show()
        if duration_ms > 0:
            self.auto_hide_timer.start(duration_ms)

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
        painter.setBrush(QBrush(QColor(255, 255, 255, 245)))
        painter.drawPath(path)
