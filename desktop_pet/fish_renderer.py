from __future__ import annotations
import math
import os
import random
import sys
from pathlib import Path
from typing import Optional, Dict, List

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal
from PySide6.QtGui import QPainter, QColor, QPixmap, QImage, QPainterPath, QBrush, QPen, QFont, QTransform
from PySide6.QtWidgets import QWidget


def resolve_asset_path(filename: str) -> Path:
    """Resolve asset path correctly in both normal dev and PyInstaller frozen runtime."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        # File is at desktop_pet/fish_renderer.py -> repo root is parent.parent
        base = Path(__file__).resolve().parent.parent
    return base / "desktop_pet" / "assets" / "whale" / filename


class Particle:
    def __init__(self, p_type: str, x: float, y: float, vx: float, vy: float, max_life: int, text: str = "", color: QColor = None):
        self.type = p_type  # 'heart', 'star', 'bubble', 'text', 'tear', 'crumb'
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = 0
        self.max_life = max_life
        self.text = text
        self.color = color or QColor(255, 180, 200)
        self.size = random.uniform(6, 12)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life += 1

    @property
    def is_alive(self) -> bool:
        return self.life < self.max_life

    @property
    def alpha(self) -> float:
        progress = self.life / self.max_life
        if progress < 0.2:
            return progress / 0.2
        return max(0.0, 1.0 - (progress - 0.2) / 0.8)


class FishRenderer(QWidget):
    """
    Whale Musume (大肥鱼 / 鲸鱼娘) Authentic Character Renderer
    Based on high-resolution Q-version artwork with authentic maid outfit, whale tail,
    whale fin ear clips, and blue-purple gradient hair.
    Provides 60 FPS smooth breathing, blinking, tail wagging, walking, jumping,
    drag-and-drop rebound physics, and all emotional/task states.
    """

    state_changed = Signal(str)
    interaction_triggered = Signal(str, str)  # (interaction_type, description)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_width = 250
        self.base_height = 270
        self.scale_factor = 1.0
        self.setFixedSize(self.base_width, self.base_height)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

        # Asset pixmap cache
        self.pixmaps: Dict[str, QPixmap] = {}
        self.mirrored_pixmaps: Dict[str, QPixmap] = {}
        self._load_assets()

        # State management
        # Supported states:
        # 'idle', 'walking_left', 'walking_right', 'jumping', 'drag', 'falling',
        # 'thinking', 'confused', 'happy', 'aggrieved', 'proud',
        # 'reading', 'computer', 'watching', 'stretch', 'sleep',
        # 'headpat', 'feed', 'touch_belly', 'touch_tail', 'afk'
        self.current_state = "idle"
        self.temp_state: Optional[str] = None
        self.temp_state_timer = 0

        # Animation counters
        self.anim_tick = 0
        self.blink_tick = 0
        self.is_blinking = False
        self.tail_wag_tick = 0
        self.is_tail_wagging = False

        # Physics & Rebound for jump and drop
        self.is_in_physics = False
        self.pos_y_offset = 0.0
        self.vel_y = 0.0
        self.gravity = 0.85
        self.bounce_damping = 0.42
        self.bounce_count = 0
        self.squash_factor = 1.0  # scale y squash on land

        # Walking step animation
        self.walk_step_phase = 0.0

        # Particles
        self.particles: List[Particle] = []

        # 60 FPS update timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(16)

    def _load_assets(self):
        asset_files = {
            "idle": "idle-cute.webp",
            "tail_swing": "tail-swing.webp",
            "wink": "wink.webp",
            "running": "running.webp",
            "pickup": "pick-up.webp",
            "thinking": "thinking.webp",
            "doubt": "meme-doubt.webp",
            "happy": "celebrate.webp",
            "happy_alt": "game-happy.webp",
            "cry": "meme-cry.webp",
            "smug": "meme-smug.webp",
            "review": "work-review.webp",
            "debug": "work-debug.webp",
            "waiting": "waiting.webp",
            "curious": "curious.webp",
            "stretch": "daily-stretch.webp",
            "sleep": "sleep.webp",
            "headpat": "react-head.webp",
            "feed": "daily-eat.webp",
            "belly": "react-belly.webp",
            "tail": "react-tail.webp",
            "afk": "afk.webp"
        }

        for key, fname in asset_files.items():
            p = resolve_asset_path(fname)
            if p.exists():
                pix = QPixmap(str(p))
                if not pix.isNull():
                    self.pixmaps[key] = pix
                    # Pre-mirror for left-facing movement
                    img = pix.toImage().mirrored(True, False)
                    self.mirrored_pixmaps[key] = QPixmap.fromImage(img)
            else:
                print(f"[FishRenderer] Warning: Asset {fname} not found at {p}")

    def set_scale(self, scale: float):
        self.scale_factor = max(0.5, min(2.5, scale))
        w = int(self.base_width * self.scale_factor)
        h = int(self.base_height * self.scale_factor)
        self.setFixedSize(w, h)
        self.update()

    def set_state(self, state: str, temp_duration_ms: int = 0):
        # Normalize alias names from backend or previous versions
        alias_map = {
            "studying": "reading",
            "resting": "sleep",
            "eat": "feed",
            "yawn": "stretch",
            "walk": "walking_right",
            "jump": "jumping",
            "excited": "happy",
            "observing": "watching",
            "code": "computer"
        }
        target_state = alias_map.get(state, state)

        if temp_duration_ms > 0:
            self.temp_state = target_state
            self.temp_state_timer = int(temp_duration_ms / 16)
        else:
            self.current_state = target_state
            self.temp_state = None

        self._spawn_state_particles(target_state)
        self.state_changed.emit(target_state)
        self.update()

    def _spawn_state_particles(self, state: str):
        cx = self.width() / 2
        cy = self.height() / 2

        if state in ["happy", "proud"]:
            for _ in range(6):
                p = Particle(
                    p_type="star",
                    x=cx + random.uniform(-40, 40),
                    y=cy - 30 + random.uniform(-20, 20),
                    vx=random.uniform(-1.5, 1.5),
                    vy=random.uniform(-2.5, -0.5),
                    max_life=45,
                    color=QColor(255, 215, 0)
                )
                self.particles.append(p)
        elif state == "headpat":
            for _ in range(5):
                p = Particle(
                    p_type="heart",
                    x=cx + random.uniform(-30, 30),
                    y=cy - 60 + random.uniform(-10, 10),
                    vx=random.uniform(-1.0, 1.0),
                    vy=random.uniform(-2.0, -0.8),
                    max_life=50,
                    color=QColor(255, 105, 180)
                )
                self.particles.append(p)
        elif state == "feed":
            for _ in range(5):
                p = Particle(
                    p_type="crumb",
                    x=cx - 15 + random.uniform(-15, 15),
                    y=cy + 10 + random.uniform(-10, 10),
                    vx=random.uniform(-0.8, 0.8),
                    vy=random.uniform(0.5, 2.0),
                    max_life=35,
                    color=QColor(222, 184, 135)
                )
                self.particles.append(p)
        elif state in ["sleep", "resting"]:
            p = Particle(
                p_type="text",
                x=cx + 25,
                y=cy - 40,
                vx=0.4,
                vy=-0.8,
                max_life=60,
                text="Zzz",
                color=QColor(120, 160, 240)
            )
            self.particles.append(p)
        elif state == "thinking":
            for i in range(3):
                p = Particle(
                    p_type="bubble",
                    x=cx + 20 + i * 8,
                    y=cy - 50 - i * 10,
                    vx=random.uniform(-0.3, 0.3),
                    vy=random.uniform(-0.8, -0.4),
                    max_life=50,
                    color=QColor(160, 210, 255)
                )
                self.particles.append(p)
        elif state in ["confused", "doubt"]:
            p = Particle(
                p_type="text",
                x=cx + 30,
                y=cy - 60,
                vx=0.2,
                vy=-0.6,
                max_life=50,
                text="？",
                color=QColor(240, 150, 80)
            )
            self.particles.append(p)
        elif state in ["aggrieved", "cry"]:
            for _ in range(4):
                p = Particle(
                    p_type="tear",
                    x=cx + random.choice([-15, 15]),
                    y=cy - 20,
                    vx=random.uniform(-0.2, 0.2),
                    vy=random.uniform(1.2, 2.5),
                    max_life=40,
                    color=QColor(100, 180, 255)
                )
                self.particles.append(p)

    def trigger_jump(self):
        """Initiate jump physics."""
        self.set_state("jumping")
        self.is_in_physics = True
        self.vel_y = -12.0
        self.pos_y_offset = 0.0
        self.bounce_count = 0

    def trigger_drop_rebound(self):
        """Initiate landing drop rebound after dragging release."""
        self.is_in_physics = True
        self.vel_y = 1.0
        self.bounce_count = 0
        self.set_state("falling")

    def _on_tick(self):
        self.anim_tick += 1

        # Handle temporary state countdown
        if self.temp_state is not None:
            self.temp_state_timer -= 1
            if self.temp_state_timer <= 0:
                self.temp_state = None
                self.state_changed.emit(self.current_state)

        active = self.temp_state or self.current_state

        # Natural blinking logic (every 200-300 ticks, blink for 8 ticks ~130ms)
        self.blink_tick += 1
        if self.blink_tick > 240 + (self.anim_tick % 80):
            self.is_blinking = True
            if self.blink_tick > 248 + (self.anim_tick % 80):
                self.is_blinking = False
                self.blink_tick = 0

        # Tail wagging cycle (every 220 ticks, wag for 24 ticks ~400ms)
        self.tail_wag_tick += 1
        if self.tail_wag_tick > 200:
            self.is_tail_wagging = True
            if self.tail_wag_tick > 226:
                self.is_tail_wagging = False
                self.tail_wag_tick = 0

        # Walking step phase
        if active in ["walking_left", "walking_right"]:
            self.walk_step_phase += 0.25

        # Physics simulation for jump / drop
        if self.is_in_physics:
            self.vel_y += self.gravity
            self.pos_y_offset += self.vel_y

            # Ground collision at offset >= 0
            if self.pos_y_offset >= 0:
                self.pos_y_offset = 0
                if abs(self.vel_y) > 2.5 and self.bounce_count < 3:
                    # Bounce up with damping
                    self.vel_y = -self.vel_y * self.bounce_damping
                    self.bounce_count += 1
                    self.squash_factor = 0.88  # landing squash
                else:
                    # Settled on ground
                    self.vel_y = 0
                    self.is_in_physics = False
                    self.squash_factor = 1.0
                    if active in ["jumping", "falling"]:
                        self.set_state("idle")
        else:
            # Recover squash smoothly
            if self.squash_factor < 1.0:
                self.squash_factor = min(1.0, self.squash_factor + 0.04)

        # Update particles
        alive_particles = []
        for p in self.particles:
            p.update()
            if p.is_alive:
                alive_particles.append(p)
        self.particles = alive_particles

        # Periodically emit sleep Zzz or subtle idle aura
        if active in ["sleep", "resting"] and self.anim_tick % 70 == 0:
            self._spawn_state_particles("sleep")

        self.update()

    def _get_active_pixmap(self) -> tuple[QPixmap, bool]:
        """
        Determines the correct QPixmap and whether it is horizontally flipped.
        Returns (pixmap, is_flipped)
        """
        active = self.temp_state or self.current_state
        flip = False

        if active == "walking_left":
            flip = True
            pix = self.mirrored_pixmaps.get("running") or self.pixmaps.get("running")
            return pix or self.pixmaps.get("idle"), flip
        elif active == "walking_right":
            pix = self.pixmaps.get("running")
            return pix or self.pixmaps.get("idle"), False
        elif active in ["jumping", "drag", "falling"]:
            pix = self.pixmaps.get("pickup") or self.pixmaps.get("happy")
            return pix, False
        elif active == "thinking":
            return self.pixmaps.get("thinking") or self.pixmaps.get("idle"), False
        elif active in ["confused", "doubt"]:
            return self.pixmaps.get("doubt") or self.pixmaps.get("idle"), False
        elif active == "happy":
            return self.pixmaps.get("happy") or self.pixmaps.get("happy_alt") or self.pixmaps.get("idle"), False
        elif active in ["aggrieved", "cry"]:
            return self.pixmaps.get("cry") or self.pixmaps.get("idle"), False
        elif active in ["proud", "smug"]:
            return self.pixmaps.get("smug") or self.pixmaps.get("idle"), False
        elif active in ["reading", "studying"]:
            return self.pixmaps.get("review") or self.pixmaps.get("idle"), False
        elif active in ["computer", "debug"]:
            return self.pixmaps.get("debug") or self.pixmaps.get("idle"), False
        elif active in ["watching", "waiting"]:
            return self.pixmaps.get("curious") or self.pixmaps.get("waiting") or self.pixmaps.get("idle"), False
        elif active in ["stretch", "yawn"]:
            return self.pixmaps.get("stretch") or self.pixmaps.get("idle"), False
        elif active in ["sleep", "resting"]:
            return self.pixmaps.get("sleep") or self.pixmaps.get("idle"), False
        elif active == "headpat":
            return self.pixmaps.get("headpat") or self.pixmaps.get("idle"), False
        elif active in ["feed", "eat"]:
            return self.pixmaps.get("feed") or self.pixmaps.get("idle"), False
        elif active == "touch_belly":
            return self.pixmaps.get("belly") or self.pixmaps.get("idle"), False
        elif active == "touch_tail":
            return self.pixmaps.get("tail") or self.pixmaps.get("idle"), False
        elif active == "afk":
            return self.pixmaps.get("afk") or self.pixmaps.get("idle"), False

        # Idle baseline with blink and tail wagging transitions
        if self.is_blinking and "wink" in self.pixmaps:
            return self.pixmaps["wink"], False
        if self.is_tail_wagging and "tail_swing" in self.pixmaps:
            return self.pixmaps["tail_swing"], False

        return self.pixmaps.get("idle"), False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        pix, flipped = self._get_active_pixmap()
        if not pix or pix.isNull():
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "大肥鱼加载中...")
            return

        w = self.width()
        h = self.height()
        active = self.temp_state or self.current_state

        # 1. Idle breathing float offset
        breath_y = 0.0
        breath_scale = 1.0
        if active == "idle":
            breath_y = math.sin(self.anim_tick * 0.05) * 2.5
            breath_scale = 1.0 + math.sin(self.anim_tick * 0.05) * 0.015

        # 2. Walk step bobbing offset
        walk_y = 0.0
        if active in ["walking_left", "walking_right"]:
            walk_y = abs(math.sin(self.walk_step_phase)) * -6.0

        # 3. Physics vertical offset (jumping/falling)
        physics_y = self.pos_y_offset

        # 4. Total vertical displacement
        total_offset_y = breath_y + walk_y + physics_y

        # Target drawing rect (keep aspect ratio of 512x512)
        # Margin to ensure character contours never get clipped
        pad_x = 10 * self.scale_factor
        pad_top = 15 * self.scale_factor
        draw_w = w - pad_x * 2
        draw_h = h - pad_top - (10 * self.scale_factor)

        # Apply squash & stretch
        sy = self.squash_factor * breath_scale
        sx = (2.0 - sy)  # preserve volume

        center_x = w / 2
        base_y = h - (12 * self.scale_factor) + total_offset_y

        painter.save()
        painter.translate(center_x, base_y)
        painter.scale(sx, sy)

        dest_rect = QRectF(-draw_w / 2, -draw_h, draw_w, draw_h)
        painter.drawPixmap(dest_rect, pix, QRectF(pix.rect()))
        painter.restore()

        # 5. Render Particle System
        for p in self.particles:
            painter.save()
            painter.setOpacity(p.alpha)
            if p.type == "star":
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(p.color))
                self._draw_star(painter, p.x, p.y, p.size)
            elif p.type == "heart":
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(p.color))
                self._draw_heart(painter, p.x, p.y, p.size)
            elif p.type == "bubble":
                painter.setPen(QPen(QColor(255, 255, 255, int(200 * p.alpha)), 1.5))
                painter.setBrush(QBrush(QColor(180, 220, 255, int(120 * p.alpha))))
                painter.drawEllipse(QPointF(p.x, p.y), p.size / 2, p.size / 2)
            elif p.type == "tear":
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(p.color))
                painter.drawEllipse(QPointF(p.x, p.y), 2.5, 4.0)
            elif p.type == "crumb":
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(p.color))
                painter.drawEllipse(QPointF(p.x, p.y), 2.0, 2.0)
            elif p.type == "text":
                painter.setPen(p.color)
                painter.setFont(QFont("Microsoft YaHei", int(10 * self.scale_factor), QFont.Weight.Bold))
                painter.drawText(QPointF(p.x, p.y), p.text)
            painter.restore()

    def _draw_star(self, painter: QPainter, cx: float, cy: float, size: float):
        path = QPainterPath()
        path.moveTo(cx, cy - size)
        path.lineTo(cx + size * 0.3, cy - size * 0.3)
        path.lineTo(cx + size, cy)
        path.lineTo(cx + size * 0.3, cy + size * 0.3)
        path.lineTo(cx, cy + size)
        path.lineTo(cx - size * 0.3, cy + size * 0.3)
        path.lineTo(cx - size, cy)
        path.lineTo(cx - size * 0.3, cy - size * 0.3)
        path.closeSubpath()
        painter.drawPath(path)

    def _draw_heart(self, painter: QPainter, cx: float, cy: float, size: float):
        path = QPainterPath()
        s = size * 0.6
        path.moveTo(cx, cy + s)
        path.cubicTo(cx - s * 1.5, cy - s * 0.5, cx - s * 1.5, cy - s * 1.8, cx, cy - s * 0.8)
        path.cubicTo(cx + s * 1.5, cy - s * 1.8, cx + s * 1.5, cy - s * 0.5, cx, cy + s)
        painter.drawPath(path)

    def hit_test_region(self, local_x: float, local_y: float) -> str:
        """
        Identify touched body area based on local widget coordinates.
        Returns: 'head', 'belly', 'tail', or 'body'
        """
        w = self.width()
        h = self.height()
        rel_x = local_x / w
        rel_y = local_y / h

        # Head region: top 36%
        if 0.25 <= rel_x <= 0.75 and 0.08 <= rel_y <= 0.38:
            return "head"
        # Belly region: center 38% to 68%
        elif 0.32 <= rel_x <= 0.68 and 0.40 <= rel_y <= 0.68:
            return "belly"
        # Tail region: back right / bottom sides
        elif rel_x > 0.65 and rel_y > 0.45:
            return "tail"
        return "body"
