from __future__ import annotations
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPainterPath
from PySide6.QtWidgets import QWidget


class VirtualRecycleBinMarker(QWidget):
    """
    Cute visible target marker on desktop showing where the Recycle Bin destination is.
    Displayed when user drops a file, guiding Whale Musume across the screen.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.ToolTip |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.SubWindow |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(90, 95)
        self.pulse_phase = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)

    def show_at(self, x: int, y: int):
        self.move(x, y)
        self.pulse_phase = 0.0
        self.timer.start(30)
        self.show()

    def dismiss(self):
        self.timer.stop()
        self.hide()

    def _on_tick(self):
        self.pulse_phase += 0.1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Background pulsing glow circle
        glow_alpha = int(120 + 60 * (1.0 + 0.5 * (1.0 if int(self.pulse_phase * 2) % 2 == 0 else -1.0)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(59, 130, 246, 35)))
        painter.drawEllipse(QRectF(5, 5, w - 10, w - 10))

        # Recycle Bin Box / Icon
        bx = w / 2 - 18
        by = 22
        bw = 36
        bh = 42

        # Bin body
        painter.setPen(QPen(QColor(37, 99, 235), 2.0))
        painter.setBrush(QBrush(QColor(239, 246, 255, 235)))
        bin_path = QPainterPath()
        bin_path.moveTo(bx + 4, by + 6)
        bin_path.lineTo(bx + bw - 4, by + 6)
        bin_path.lineTo(bx + bw - 6, by + bh)
        bin_path.lineTo(bx + 6, by + bh)
        bin_path.closeSubpath()
        painter.drawPath(bin_path)

        # Bin lid
        painter.setBrush(QBrush(QColor(59, 130, 246, 230)))
        painter.drawRoundedRect(QRectF(bx - 2, by, bw + 4, 7), 2, 2)
        # Lid handle
        painter.drawRoundedRect(QRectF(bx + bw / 2 - 5, by - 4, 10, 4), 2, 2)

        # 3 vertical slot lines
        painter.setPen(QPen(QColor(147, 197, 253), 1.5))
        painter.drawLine(QPointF(bx + 11, by + 13), QPointF(bx + 12, by + bh - 6))
        painter.drawLine(QPointF(bx + bw / 2, by + 13), QPointF(bx + bw / 2, by + bh - 6))
        painter.drawLine(QPointF(bx + bw - 11, by + 13), QPointF(bx + bw - 12, by + bh - 6))

        # Bottom label
        painter.setPen(QColor(30, 64, 175))
        painter.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
        painter.drawText(QRectF(0, h - 22, w, 20), Qt.AlignmentFlag.AlignCenter, "Windows 回收站")
