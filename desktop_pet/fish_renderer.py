from __future__ import annotations
import math
import random
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPainterPath, QLinearGradient, QRadialGradient, QBrush, QPen, QFont
from PySide6.QtWidgets import QWidget


class FishRenderer(QWidget):
    """
    Q版二次元【鲨鱼娘 / 鲸鱼娘】(Shark Musume / Whale Girl) 实时矢量动画渲染器
    参考社区爆火的鲸鱼娘/鲨鱼娘二次元同人看板娘设计：
    - 呆萌可爱的蓝渐变短发、萌系呆毛、灵动大眼与水手服裙装
    - 身后标志性的大号软萌鲨鱼尾巴，随呼吸与动作左右摇摆
    - 头戴标志性的迷你鲨鱼鳍/鲸鱼鳍发饰
    - 6大生动动画状态：
        1. idle: 待机站立，自然微呼吸，大尾巴悠悠摆动，灵动眨眼
        2. thinking: 歪头思索，单手轻托腮，头顶冒出思考泡泡
        3. happy: 开心蹦跳，双手欢呼举起，笑弯眼，金黄星光粒子飞舞
        4. confused: 歪头挠头，呆毛翘起，头顶浮现问号与小汗珠
        5. studying: 戴着金丝圆眼镜，专注抱着一台发光的小笔记本电脑写笔记
        6. resting: 抱着软绵绵的鲸鱼小抱枕，闭目点头打瞌睡，飘出'zZ'梦境气泡
    - 交互特性：
        - 头部区域支持鼠标悬停抚摸（摸头心动/脸红效果）
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(240, 270)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

        self.current_state = "idle"  # idle, thinking, happy, confused, studying, resting
        self.anim_tick = 0
        self.blink_tick = 0
        self.is_blinking = False
        self.is_head_patting = False
        self.pat_timer = 0

        # Particle systems
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

    def mouseMoveEvent(self, event):
        # Head pat area check (x: 80~160, y: 40~100)
        x = event.position().x()
        y = event.position().y()
        if 80 <= x <= 160 and 40 <= y <= 110:
            self.is_head_patting = True
            self.pat_timer = 30
        super().mouseMoveEvent(event)

    def _on_tick(self):
        self.anim_tick += 1

        if self.pat_timer > 0:
            self.pat_timer -= 1
            if self.pat_timer == 0:
                self.is_head_patting = False

        # Blinking logic
        if self.current_state != "resting" and not self.is_head_patting:
            self.blink_tick += 1
            if self.blink_tick > 160 and random.random() < 0.06:
                self.is_blinking = True
            if self.is_blinking and self.blink_tick > 175:
                self.is_blinking = False
                self.blink_tick = 0
        else:
            self.is_blinking = False

        # Particle generators based on state
        if (self.current_state == "thinking") and self.anim_tick % 24 == 0:
            self.particles.append({
                "type": "bubble",
                "x": 170 + random.uniform(-10, 15),
                "y": 80,
                "r": random.uniform(3, 7),
                "life": 45,
                "max_life": 45
            })
        elif (self.current_state == "happy" or self.is_head_patting) and self.anim_tick % 14 == 0:
            self.particles.append({
                "type": "star" if random.random() > 0.4 else "heart",
                "x": random.uniform(40, 200),
                "y": random.uniform(40, 100),
                "r": random.uniform(5, 9),
                "life": 32,
                "max_life": 32
            })
        elif self.current_state == "resting" and self.anim_tick % 40 == 0:
            self.particles.append({
                "type": "zZ",
                "x": 160,
                "y": 90,
                "life": 60,
                "max_life": 60
            })

        # Update particles
        alive = []
        for p in self.particles:
            p["life"] -= 1
            if p["type"] == "bubble":
                p["y"] -= 1.1
                p["x"] += math.sin(p["life"] * 0.15) * 0.7
            elif p["type"] in ["star", "heart"]:
                p["y"] -= 0.9
            elif p["type"] == "zZ":
                p["y"] -= 0.6
                p["x"] += 0.4
            if p["life"] > 0:
                alive.append(p)
        self.particles = alive

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        t = self.anim_tick * 0.05
        float_y = 0.0
        tilt = 0.0
        scale_x = 1.0

        if self.current_state == "idle":
            float_y = math.sin(t) * 4.0
            tilt = math.cos(t * 0.7) * 1.5
        elif self.current_state == "thinking":
            float_y = math.sin(t * 0.8) * 2.5
            tilt = -6.0
        elif self.current_state == "happy" or self.is_head_patting:
            float_y = -abs(math.sin(t * 2.2)) * 14.0
            tilt = math.sin(t * 2.2) * 5.0
            scale_x = 1.0 + math.cos(t * 2.2) * 0.06
        elif self.current_state == "confused":
            float_y = math.sin(t) * 3.0
            tilt = 10.0
        elif self.current_state == "studying":
            float_y = math.sin(t * 0.5) * 2.0
            tilt = 1.0
        elif self.current_state == "resting":
            float_y = math.sin(t * 0.35) * 2.0
            tilt = 2.0

        center_x = 120
        center_y = 140 + float_y

        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(tilt)
        painter.scale(scale_x, 2.0 - scale_x)

        # 1. Back Layer: Big Shark Tail (Behind body, swaying)
        tail_speed = 3.0 if (self.current_state == "happy" or self.is_head_patting) else 1.2
        tail_angle = math.sin(t * tail_speed) * 16.0
        self._draw_shark_tail(painter, -15, 45, tail_angle)

        # 2. Back Hair
        self._draw_back_hair(painter)

        # 3. Chibi Body & Sailor Dress
        self._draw_dress_and_legs(painter)

        # 4. Arms & Hand Props (Laptop, Cushion, Hand waves)
        self._draw_arms_and_props(painter)

        # 5. Chibi Head & Cute Face
        self._draw_head_and_face(painter)

        # 6. Shark Fin Headwear & Ahoge (呆毛)
        self._draw_shark_headwear(painter)

        painter.restore()

        # 7. Render Particles (Screen coords)
        self._draw_particles(painter)

    def _draw_shark_tail(self, p: QPainter, x: float, y: float, angle: float):
        p.save()
        p.translate(x, y)
        p.rotate(angle)

        # Large, chubby shark tail extending back and curving up
        path = QPainterPath()
        path.moveTo(0, 0)
        # Tail top curve
        path.cubicTo(-40, 5, -80, -25, -95, -55)
        # Upper fin lobe
        path.cubicTo(-115, -75, -125, -60, -105, -35)
        # Fin fork notch
        path.lineTo(-90, -30)
        # Lower fin lobe
        path.cubicTo(-110, -15, -100, 5, -80, 5)
        # Underbelly curve back to base
        path.cubicTo(-50, 15, -20, 18, 0, 10)
        path.closeSubpath()

        # Gradient: Navy ocean blue to bright azure
        grad = QLinearGradient(0, 0, -100, -50)
        grad.setColorAt(0.0, QColor(41, 128, 220))
        grad.setColorAt(0.6, QColor(30, 95, 180))
        grad.setColorAt(1.0, QColor(15, 60, 130))

        p.setPen(QPen(QColor(18, 55, 110), 2.5))
        p.setBrush(QBrush(grad))
        p.drawPath(path)

        # White underside patch of the shark tail
        white_path = QPainterPath()
        white_path.moveTo(0, 10)
        white_path.cubicTo(-20, 18, -50, 15, -80, 5)
        white_path.cubicTo(-70, -2, -30, 2, 0, 4)
        white_path.closeSubpath()

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(245, 250, 255, 230)))
        p.drawPath(white_path)

        p.restore()

    def _draw_back_hair(self, p: QPainter):
        # Soft blue hair spreading behind the neck
        path = QPainterPath()
        path.moveTo(-36, -10)
        path.cubicTo(-50, 20, -45, 50, -35, 55)
        path.cubicTo(-25, 45, -25, 25, -20, 15)
        path.lineTo(20, 15)
        path.cubicTo(25, 25, 25, 45, 35, 55)
        path.cubicTo(45, 50, 50, 20, 36, -10)
        path.closeSubpath()

        grad = QLinearGradient(0, -10, 0, 55)
        grad.setColorAt(0.0, QColor(60, 140, 235))
        grad.setColorAt(1.0, QColor(35, 90, 180))

        p.setPen(QPen(QColor(20, 60, 125), 2.0))
        p.setBrush(QBrush(grad))
        p.drawPath(path)

    def _draw_dress_and_legs(self, p: QPainter):
        # 1. Little legs and shoes
        leg_color = QColor(255, 255, 255)  # White knee socks
        p.setPen(QPen(QColor(200, 215, 235), 1.5))
        p.setBrush(QBrush(leg_color))
        p.drawRoundedRect(QRectF(-16, 50, 11, 24), 5, 5)
        p.drawRoundedRect(QRectF(5, 50, 11, 24), 5, 5)

        # Shoes (Dark navy mary-janes)
        shoe_color = QColor(25, 50, 95)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(shoe_color))
        p.drawRoundedRect(QRectF(-18, 68, 14, 9), 4, 4)
        p.drawRoundedRect(QRectF(4, 68, 14, 9), 4, 4)

        # 2. Sailor Dress (Skirt + Top)
        skirt_path = QPainterPath()
        skirt_path.moveTo(-22, 28)
        skirt_path.lineTo(-34, 52)
        skirt_path.cubicTo(-15, 57, 15, 57, 34, 52)
        skirt_path.lineTo(22, 28)
        skirt_path.closeSubpath()

        dress_grad = QLinearGradient(0, 15, 0, 55)
        dress_grad.setColorAt(0.0, QColor(35, 75, 145))
        dress_grad.setColorAt(1.0, QColor(20, 50, 105))

        p.setPen(QPen(QColor(15, 40, 85), 2.0))
        p.setBrush(QBrush(dress_grad))
        p.drawPath(skirt_path)

        # White skirt hem stripes
        p.setPen(QPen(QColor(255, 255, 255, 220), 2.0))
        p.drawArc(QRectF(-32, 45, 64, 10), 10 * 16, 160 * 16)

        # Shirt Torso
        torso_path = QPainterPath()
        torso_path.moveTo(-20, 10)
        torso_path.lineTo(-22, 30)
        torso_path.lineTo(22, 30)
        torso_path.lineTo(20, 10)
        torso_path.closeSubpath()

        p.setPen(QPen(QColor(200, 215, 235), 1.5))
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.drawPath(torso_path)

        # Sailor collar & Red Tie
        collar = QPainterPath()
        collar.moveTo(-22, 10)
        collar.lineTo(0, 24)
        collar.lineTo(22, 10)
        collar.lineTo(16, 5)
        collar.lineTo(-16, 5)
        collar.closeSubpath()

        p.setPen(QPen(QColor(20, 50, 105), 1.5))
        p.setBrush(QBrush(QColor(40, 95, 180)))
        p.drawPath(collar)

        # Red ribbon tie
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(235, 65, 85)))
        p.drawEllipse(QRectF(-4, 18, 8, 8))
        tie_path = QPainterPath()
        tie_path.moveTo(-2, 24)
        tie_path.lineTo(-6, 32)
        tie_path.lineTo(0, 30)
        tie_path.lineTo(6, 32)
        tie_path.lineTo(2, 24)
        tie_path.closeSubpath()
        p.drawPath(tie_path)

    def _draw_arms_and_props(self, p: QPainter):
        skin_color = QColor(255, 226, 214)

        if self.current_state == "studying":
            # Holding a cute mini laptop
            # Laptop base
            p.setPen(QPen(QColor(80, 120, 180), 2.0))
            p.setBrush(QBrush(QColor(225, 235, 250)))
            p.drawRoundedRect(QRectF(-24, 22, 48, 16), 3, 3)

            # Glowing Laptop Screen
            p.setBrush(QBrush(QColor(170, 225, 255, 240)))
            p.drawRoundedRect(QRectF(-20, 8, 40, 20), 3, 3)
            # Little fish logo on back of screen
            p.setPen(QPen(QColor(40, 120, 220), 1.5))
            p.drawArc(QRectF(-6, 14, 12, 8), 0, 360 * 16)

            # Cute hands holding sides of laptop
            p.setPen(QPen(QColor(230, 180, 160), 1.5))
            p.setBrush(QBrush(skin_color))
            p.drawEllipse(QRectF(-26, 22, 10, 10))
            p.drawEllipse(QRectF(16, 22, 10, 10))

        elif self.current_state == "resting":
            # Hugging a cute shark plushie pillow
            plush = QPainterPath()
            plush.moveTo(-22, 16)
            plush.cubicTo(-28, 30, -22, 40, 0, 38)
            plush.cubicTo(22, 40, 28, 30, 22, 16)
            plush.cubicTo(10, 14, -10, 14, -22, 16)
            plush.closeSubpath()

            p.setPen(QPen(QColor(30, 80, 150), 2.0))
            p.setBrush(QBrush(QColor(90, 175, 245)))
            p.drawPath(plush)
            # Plush eyes (^ ^)
            p.setPen(QPen(QColor(20, 50, 90), 1.5))
            p.drawArc(QRectF(-12, 22, 7, 5), 0, 180 * 16)
            p.drawArc(QRectF(5, 22, 7, 5), 0, 180 * 16)

            # Arms wrapped around
            p.setPen(QPen(QColor(230, 180, 160), 1.5))
            p.setBrush(QBrush(skin_color))
            p.drawEllipse(QRectF(-25, 22, 10, 10))
            p.drawEllipse(QRectF(15, 22, 10, 10))

        elif self.current_state == "happy" or self.is_head_patting:
            # Both hands raised up in joy!
            p.setPen(QPen(QColor(230, 180, 160), 1.5))
            p.setBrush(QBrush(skin_color))
            # Sleeves up
            p.setPen(QPen(QColor(20, 50, 105), 1.5))
            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.drawRoundedRect(QRectF(-32, 6, 12, 18), 4, 4)
            p.drawRoundedRect(QRectF(20, 6, 12, 18), 4, 4)
            # Hands
            p.setBrush(QBrush(skin_color))
            p.drawEllipse(QRectF(-34, -2, 10, 10))
            p.drawEllipse(QRectF(24, -2, 10, 10))

        elif self.current_state == "thinking":
            # One hand touching chin
            p.setPen(QPen(QColor(230, 180, 160), 1.5))
            p.setBrush(QBrush(skin_color))
            p.drawEllipse(QRectF(10, 4, 9, 9))
            p.drawEllipse(QRectF(-22, 22, 9, 9))

        elif self.current_state == "confused":
            # Hand behind head, scratching head
            p.setPen(QPen(QColor(230, 180, 160), 1.5))
            p.setBrush(QBrush(skin_color))
            p.drawEllipse(QRectF(24, -14, 9, 9))
            p.drawEllipse(QRectF(-22, 24, 9, 9))

        else:
            # Idle: hands naturally at sides
            p.setPen(QPen(QColor(230, 180, 160), 1.5))
            p.setBrush(QBrush(skin_color))
            p.drawEllipse(QRectF(-26, 22, 10, 10))
            p.drawEllipse(QRectF(16, 22, 10, 10))

    def _draw_head_and_face(self, p: QPainter):
        skin_color = QColor(255, 235, 226)

        # 1. Chibi Face shape
        head_path = QPainterPath()
        head_path.addRoundedRect(QRectF(-38, -48, 76, 62), 30, 30)

        p.setPen(QPen(QColor(235, 195, 175), 1.5))
        p.setBrush(QBrush(skin_color))
        p.drawPath(head_path)

        # 2. Anime Big Eyes
        eye_y = -18
        if self.current_state == "resting":
            # Calm sleeping curved lashes
            p.setPen(QPen(QColor(30, 55, 95), 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            path_l = QPainterPath()
            path_l.moveTo(-26, eye_y)
            path_l.cubicTo(-20, eye_y + 6, -14, eye_y + 6, -8, eye_y)
            p.drawPath(path_l)

            path_r = QPainterPath()
            path_r.moveTo(8, eye_y)
            path_r.cubicTo(14, eye_y + 6, 20, eye_y + 6, 26, eye_y)
            p.drawPath(path_r)

        elif self.current_state == "happy" or self.is_head_patting:
            # Joyful happy arcs (^ ^)
            p.setPen(QPen(QColor(25, 50, 90), 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            path_l = QPainterPath()
            path_l.moveTo(-26, eye_y + 2)
            path_l.cubicTo(-20, eye_y - 7, -14, eye_y - 7, -8, eye_y + 2)
            p.drawPath(path_l)

            path_r = QPainterPath()
            path_r.moveTo(8, eye_y + 2)
            path_r.cubicTo(14, eye_y - 7, 20, eye_y - 7, 26, eye_y + 2)
            p.drawPath(path_r)

        elif self.is_blinking:
            # Blinking line
            p.setPen(QPen(QColor(25, 50, 90), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(-25, eye_y, -9, eye_y)
            p.drawLine(9, eye_y, 25, eye_y)

        else:
            # Deep sparkling anime eyes
            for eye_x in [-18, 18]:
                # Sclera / eye background
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor(255, 255, 255)))
                p.drawEllipse(QRectF(eye_x - 10, eye_y - 12, 20, 24))

                # Ocean Blue Gradient Iris
                iris_grad = QLinearGradient(eye_x, eye_y - 12, eye_x, eye_y + 12)
                iris_grad.setColorAt(0.0, QColor(20, 45, 95))
                iris_grad.setColorAt(0.5, QColor(35, 110, 215))
                iris_grad.setColorAt(1.0, QColor(100, 200, 255))

                p.setBrush(QBrush(iris_grad))
                p.drawEllipse(QRectF(eye_x - 8, eye_y - 10, 16, 20))

                # Pupil
                p.setBrush(QBrush(QColor(15, 30, 65)))
                p.drawEllipse(QRectF(eye_x - 4, eye_y - 4, 8, 10))

                # Big sparkling light reflection
                p.setBrush(QBrush(QColor(255, 255, 255, 240)))
                p.drawEllipse(QRectF(eye_x - 5, eye_y - 8, 6, 6))
                p.drawEllipse(QRectF(eye_x + 1, eye_y + 2, 3, 3))

                # Top Eyelashes
                p.setPen(QPen(QColor(20, 40, 80), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawArc(QRectF(eye_x - 10, eye_y - 14, 20, 10), 20 * 16, 140 * 16)

        # 3. Cute Blush (粉嫩红晕)
        blush_color = QColor(255, 130, 160, 180 if self.is_head_patting else 120)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(blush_color))
        p.drawEllipse(QRectF(-32, -8, 14, 8))
        p.drawEllipse(QRectF(18, -8, 14, 8))

        # 4. Tiny Cute Mouth
        p.setPen(QPen(QColor(200, 60, 90), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        if self.current_state in ["happy", "studying"] or self.is_head_patting:
            mouth = QPainterPath()
            mouth.moveTo(-5, 0)
            mouth.cubicTo(-2, 6, 2, 6, 5, 0)
            p.drawPath(mouth)
        elif self.current_state in ["thinking", "confused"]:
            p.setBrush(QBrush(QColor(255, 140, 160)))
            p.drawEllipse(QRectF(-2, 1, 5, 5))
        else:
            mouth = QPainterPath()
            mouth.moveTo(-4, 1)
            mouth.cubicTo(-1, 4, 2, 4, 4, 1)
            p.drawPath(mouth)

        # 5. Front Bangs & Side Locks (海蓝色渐变刘海)
        hair_path = QPainterPath()
        hair_path.moveTo(-40, -32)
        hair_path.cubicTo(-44, -10, -42, 15, -34, 24)  # Left side lock
        hair_path.lineTo(-28, 5)
        hair_path.cubicTo(-24, -15, -12, -18, -6, -24)  # Left fringe
        hair_path.cubicTo(0, -18, 10, -15, 18, -26)     # Middle fringe
        hair_path.cubicTo(26, -18, 30, 5, 34, 24)       # Right side lock
        hair_path.cubicTo(42, 15, 44, -10, 40, -32)
        hair_path.cubicTo(30, -58, -30, -58, -40, -32)
        hair_path.closeSubpath()

        hair_grad = QLinearGradient(0, -55, 0, 25)
        hair_grad.setColorAt(0.0, QColor(70, 150, 245))
        hair_grad.setColorAt(0.7, QColor(45, 115, 215))
        hair_grad.setColorAt(1.0, QColor(90, 200, 255))  # Highlight tips

        p.setPen(QPen(QColor(20, 65, 135), 2.0))
        p.setBrush(QBrush(hair_grad))
        p.drawPath(hair_path)

        # 6. Glasses for 'studying' state
        if self.current_state == "studying":
            p.setPen(QPen(QColor(235, 175, 50), 2.0))
            p.setBrush(QBrush(QColor(255, 255, 255, 50)))
            p.drawEllipse(QRectF(-28, -24, 20, 20))
            p.drawEllipse(QRectF(8, -24, 20, 20))
            p.drawLine(-8, -14, 8, -14)

    def _draw_shark_headwear(self, p: QPainter):
        # 1. Cute Shark Fin Hairclip on right side
        fin = QPainterPath()
        fin.moveTo(18, -46)
        fin.cubicTo(25, -68, 42, -72, 38, -48)
        fin.closeSubpath()

        p.setPen(QPen(QColor(15, 50, 110), 2.0))
        p.setBrush(QBrush(QColor(40, 110, 200)))
        p.drawPath(fin)

        # 2. Bouncing Ahoge (萌萌呆毛)
        t = self.anim_tick * 0.08
        ahoge_sway = math.sin(t) * 5.0
        ahoge = QPainterPath()
        ahoge.moveTo(0, -48)
        ahoge.cubicTo(-8 + ahoge_sway, -65, 12 + ahoge_sway, -75, 4 + ahoge_sway, -82)

        p.setPen(QPen(QColor(50, 125, 225), 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.PenStyle.NoPen)
        p.drawPath(ahoge)

        # 3. Confused Question Mark
        if self.current_state == "confused":
            p.setPen(QPen(QColor(255, 180, 40), 3.0))
            font = QFont("Arial", 18, QFont.Weight.Bold)
            p.setFont(font)
            p.drawText(QPointF(40, -45), "？")

    def _draw_particles(self, p: QPainter):
        for part in self.particles:
            alpha = int(255 * (part["life"] / part["max_life"]))
            if part["type"] == "bubble":
                p.setPen(QPen(QColor(180, 225, 255, alpha), 1.5))
                p.setBrush(QBrush(QColor(255, 255, 255, int(alpha * 0.4))))
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
            elif part["type"] == "heart":
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor(255, 120, 150, alpha)))
                x, y = part["x"], part["y"]
                path = QPainterPath()
                path.moveTo(x, y + 4)
                path.cubicTo(x - 6, y - 4, x - 6, y - 8, x, y - 4)
                path.cubicTo(x + 6, y - 8, x + 6, y - 4, x, y + 4)
                p.drawPath(path)
            elif part["type"] == "zZ":
                p.setPen(QPen(QColor(130, 185, 255, alpha), 2.2))
                font = QFont("Comic Sans MS", 13, QFont.Weight.Bold)
                p.setFont(font)
                p.drawText(QPointF(part["x"], part["y"]), "zZ")
