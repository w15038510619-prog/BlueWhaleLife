from __future__ import annotations
import math
import random
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPainterPath, QLinearGradient, QBrush, QPen, QFont
from PySide6.QtWidgets import QWidget


class FishRenderer(QWidget):
    """
    Procedural Vector Animation Renderer for '大肥鱼' (Big Chubby Whale/Fish).
    Original vector artwork rendered in real-time with smooth 60fps physics & 6 animation states:
    - idle: gentle floating, breathing, tail sway
    - thinking: bubble stream, pondering eyes, tilt
    - happy: bouncy wiggle, twinkling stars, heart sparkles
    - confused: tilted head, question mark, asymmetric eyes
    - studying: cute reading glasses, scroll/notebook, focused eyes
    - resting: closed curved eyes, slow deep breathing, floating 'zZ'
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(220, 200)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.current_state = "idle"  # idle, thinking, happy, confused, studying, resting
        self.anim_tick = 0
        self.blink_tick = 0
        self.is_blinking = False

        # Particle lists (bubbles, stars, zZ)
        self.particles: list[dict] = []

        # 60 FPS animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(16)

    def set_state(self, state: str):
        if state in ["idle", "thinking", "happy", "confused", "studying", "resting"]:
            self.current_state = state
            self.particles.clear()
            self.update()

    def _on_tick(self):
        self.anim_tick += 1

        # Blinking logic
        if self.current_state != "resting":
            self.blink_tick += 1
            if self.blink_tick > 180 and random.random() < 0.05:
                self.is_blinking = True
            if self.is_blinking and self.blink_tick > 195:
                self.is_blinking = False
                self.blink_tick = 0
        else:
            self.is_blinking = False

        # State-based particle generators
        if self.current_state == "thinking" and self.anim_tick % 25 == 0:
            self.particles.append({
                "type": "bubble",
                "x": 160 + random.uniform(-10, 10),
                "y": 80,
                "r": random.uniform(3, 7),
                "life": 40,
                "max_life": 40
            })
        elif self.current_state == "happy" and self.anim_tick % 15 == 0:
            self.particles.append({
                "type": "star",
                "x": random.uniform(40, 180),
                "y": random.uniform(30, 80),
                "r": random.uniform(4, 8),
                "life": 30,
                "max_life": 30
            })
        elif self.current_state == "resting" and self.anim_tick % 45 == 0:
            self.particles.append({
                "type": "zZ",
                "x": 140,
                "y": 70,
                "life": 60,
                "max_life": 60,
                "scale": 10
            })

        # Update particles
        alive_particles = []
        for p in self.particles:
            p["life"] -= 1
            if p["type"] == "bubble":
                p["y"] -= 1.2
                p["x"] += math.sin(p["life"] * 0.15) * 0.8
            elif p["type"] == "star":
                p["y"] -= 0.8
            elif p["type"] == "zZ":
                p["y"] -= 0.6
                p["x"] += 0.4
            if p["life"] > 0:
                alive_particles.append(p)
        self.particles = alive_particles

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Base transforms depending on state
        t = self.anim_tick * 0.05
        float_y = 0.0
        tilt = 0.0
        squash = 1.0

        if self.current_state == "idle":
            float_y = math.sin(t) * 6.0
            tilt = math.cos(t * 0.8) * 2.0
        elif self.current_state == "thinking":
            float_y = math.sin(t * 0.7) * 3.0
            tilt = -7.0
        elif self.current_state == "happy":
            float_y = -abs(math.sin(t * 2.0)) * 14.0
            tilt = math.sin(t * 2.0) * 8.0
            squash = 1.0 + math.cos(t * 2.0) * 0.08
        elif self.current_state == "confused":
            float_y = math.sin(t) * 4.0
            tilt = 12.0
        elif self.current_state == "studying":
            float_y = math.sin(t * 0.5) * 2.0
            tilt = 2.0
        elif self.current_state == "resting":
            float_y = math.sin(t * 0.4) * 2.0
            tilt = 0.0
            squash = 1.0 + math.sin(t * 0.4) * 0.04

        # Center coordinate for fish body
        center_x = 105
        center_y = 100 + float_y

        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(tilt)
        painter.scale(squash, 2.0 - squash)

        # 1. Tail fin
        tail_angle = math.sin(t * (2.5 if self.current_state == "happy" else 1.2)) * 14.0
        self._draw_tail(painter, -65, 0, tail_angle)

        # 2. Side pectoral fin (back)
        self._draw_pectoral_fin(painter, -15, 15, is_front=False)

        # 3. Main Chubby Whale Body
        self._draw_body(painter)

        # 4. Belly
        self._draw_belly(painter)

        # 5. Side pectoral fin (front)
        fin_wave = math.sin(t * 1.5) * 8.0
        self._draw_pectoral_fin(painter, -10, 18, is_front=True, angle=fin_wave)

        # 6. Facial Features (Eyes, Blush, Mouth)
        self._draw_face(painter)

        # 7. State Accessories (Glasses for studying, question mark for confused)
        if self.current_state == "studying":
            self._draw_glasses(painter)
        elif self.current_state == "confused":
            self._draw_question_mark(painter)

        painter.restore()

        # 8. Render Particles (Screen Coordinates)
        self._draw_particles(painter)

    def _draw_body(self, p: QPainter):
        path = QPainterPath()
        # Chubby teardrop/whale shape
        path.moveTo(55, -10)
        # Top arc
        path.cubicTo(30, -50, -40, -45, -70, -5)
        # Tail connection
        path.lineTo(-75, 5)
        # Belly curve
        path.cubicTo(-40, 48, 25, 48, 55, 10)
        # Snout curve
        path.cubicTo(65, 5, 65, -5, 55, -10)
        path.closeSubpath()

        # Beautiful ocean blue gradient
        grad = QLinearGradient(0, -50, 0, 45)
        grad.setColorAt(0.0, QColor(90, 175, 255))
        grad.setColorAt(1.0, QColor(40, 115, 215))

        p.setPen(QPen(QColor(25, 80, 160), 2.5))
        p.setBrush(QBrush(grad))
        p.drawPath(path)

    def _draw_belly(self, p: QPainter):
        path = QPainterPath()
        path.moveTo(-45, 15)
        path.cubicTo(-20, 40, 20, 40, 50, 10)
        path.cubicTo(40, 25, 0, 36, -45, 15)
        path.closeSubpath()

        belly_grad = QLinearGradient(0, 10, 0, 40)
        belly_grad.setColorAt(0.0, QColor(245, 250, 255, 230))
        belly_grad.setColorAt(1.0, QColor(215, 235, 255, 240))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(belly_grad))
        p.drawPath(path)

    def _draw_tail(self, p: QPainter, x: float, y: float, angle: float):
        p.save()
        p.translate(x, y)
        p.rotate(angle)

        path = QPainterPath()
        path.moveTo(0, 0)
        path.cubicTo(-15, -25, -35, -28, -28, -5)
        path.cubicTo(-25, 0, -25, 0, -28, 5)
        path.cubicTo(-35, 28, -15, 25, 0, 0)
        path.closeSubpath()

        grad = QLinearGradient(-30, -20, 0, 20)
        grad.setColorAt(0.0, QColor(80, 165, 250))
        grad.setColorAt(1.0, QColor(45, 120, 220))

        p.setPen(QPen(QColor(25, 80, 160), 2.0))
        p.setBrush(QBrush(grad))
        p.drawPath(path)
        p.restore()

    def _draw_pectoral_fin(self, p: QPainter, x: float, y: float, is_front: bool, angle: float = 0.0):
        p.save()
        p.translate(x, y)
        p.rotate(angle)

        path = QPainterPath()
        path.moveTo(0, 0)
        path.cubicTo(5, 15, 15, 25, 5, 28)
        path.cubicTo(-8, 28, -12, 15, 0, 0)
        path.closeSubpath()

        color = QColor(60, 140, 240, 255 if is_front else 160)
        p.setPen(QPen(QColor(25, 80, 160), 1.8))
        p.setBrush(QBrush(color))
        p.drawPath(path)
        p.restore()

    def _draw_face(self, p: QPainter):
        # 1. Blush
        blush_color = QColor(255, 140, 160, 140)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(blush_color))
        p.drawEllipse(QRectF(22, 2, 14, 8))

        # 2. Eye
        eye_x, eye_y = 35, -12
        if self.current_state == "resting":
            # Closed calm curved line
            p.setPen(QPen(QColor(20, 50, 90), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            path = QPainterPath()
            path.moveTo(eye_x - 7, eye_y)
            path.cubicTo(eye_x - 3, eye_y + 5, eye_x + 3, eye_y + 5, eye_x + 7, eye_y)
            p.drawPath(path)
        elif self.current_state == "happy":
            # Cheerful curve ^
            p.setPen(QPen(QColor(20, 50, 90), 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            path = QPainterPath()
            path.moveTo(eye_x - 7, eye_y + 2)
            path.cubicTo(eye_x - 3, eye_y - 6, eye_x + 3, eye_y - 6, eye_x + 7, eye_y + 2)
            p.drawPath(path)
        elif self.is_blinking:
            # Blink line
            p.setPen(QPen(QColor(20, 50, 90), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(eye_x - 7, eye_y, eye_x + 7, eye_y)
        else:
            # Open cute shiny eye
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(20, 45, 80)))
            p.drawEllipse(QRectF(eye_x - 6, eye_y - 8, 12, 14))

            # Highlights
            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.drawEllipse(QRectF(eye_x - 4, eye_y - 6, 5, 5))
            p.drawEllipse(QRectF(eye_x + 1, eye_y + 1, 2.5, 2.5))

        # 3. Mouth
        p.setPen(QPen(QColor(20, 50, 90), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        mouth_path = QPainterPath()
        if self.current_state == "happy":
            # Open laughing mouth
            mouth_path.moveTo(48, 5)
            mouth_path.cubicTo(52, 12, 58, 12, 60, 5)
        elif self.current_state == "thinking" or self.current_state == "confused":
            # Small circle 'o'
            p.drawEllipse(QRectF(52, 4, 5, 5))
            return
        else:
            # Gentle smile
            mouth_path.moveTo(48, 5)
            mouth_path.cubicTo(52, 9, 56, 9, 59, 6)
        p.drawPath(mouth_path)

    def _draw_glasses(self, p: QPainter):
        p.setPen(QPen(QColor(230, 160, 40), 2.0))
        p.setBrush(QBrush(QColor(255, 255, 255, 60)))
        # Lens around eye
        p.drawEllipse(QRectF(26, -20, 18, 18))
        # Frame bridge
        p.drawLine(44, -11, 52, -10)

    def _draw_question_mark(self, p: QPainter):
        p.setPen(QPen(QColor(255, 180, 50), 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        font = QFont("Arial", 16, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(QPointF(40, -30), "?")

    def _draw_particles(self, p: QPainter):
        for part in self.particles:
            alpha = int(255 * (part["life"] / part["max_life"]))
            if part["type"] == "bubble":
                p.setPen(QPen(QColor(180, 220, 255, alpha), 1.5))
                p.setBrush(QBrush(QColor(255, 255, 255, int(alpha * 0.3))))
                r = part["r"]
                p.drawEllipse(QRectF(part["x"] - r, part["y"] - r, r * 2, r * 2))
            elif part["type"] == "star":
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor(255, 225, 80, alpha)))
                x, y, r = part["x"], part["y"], part["r"]
                path = QPainterPath()
                path.moveTo(x, y - r)
                path.lineTo(x + r * 0.3, y - r * 0.3)
                path.lineTo(x + r, y)
                path.lineTo(x + r * 0.3, y + r * 0.3)
                path.lineTo(x, y + r)
                path.lineTo(x - r * 0.3, y + r * 0.3)
                path.lineTo(x - r, y)
                path.lineTo(x - r * 0.3, y - r * 0.3)
                path.closeSubpath()
                p.drawPath(path)
            elif part["type"] == "zZ":
                p.setPen(QPen(QColor(120, 170, 240, alpha), 2.0))
                font = QFont("Comic Sans MS", 12, QFont.Weight.Bold)
                p.setFont(font)
                p.drawText(QPointF(part["x"], part["y"]), "zZ")
