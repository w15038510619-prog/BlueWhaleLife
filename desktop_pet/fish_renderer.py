from __future__ import annotations
import math
import os
import random
import sys
from pathlib import Path
from typing import Optional, Dict, List, Tuple

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QPainter, QColor, QPixmap, QImage, QPainterPath,
    QBrush, QPen, QFont, QTransform
)
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
        self.type = p_type  # 'heart', 'star', 'bubble', 'text', 'tear', 'crumb', 'sparkle'
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
    Based on high-resolution DeepSeek Whale Musume chibi artwork.
    Provides 60 FPS smooth breathing, blinking, tail wagging, walking, jumping,
    drag-and-drop rebound physics, carrying/throwing file animations, and all emotional states.
    """

    state_changed = Signal(str)
    interaction_triggered = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_width = 250
        self.base_height = 270
        self.scale_factor = 1.0
        self.setFixedSize(self.base_width, self.base_height)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)

        # Asset pixmap cache
        self.pixmaps: Dict[str, QPixmap] = {}
        self.mirrored_pixmaps: Dict[str, QPixmap] = {}
        self._load_assets()

        # State management
        self.current_state = "idle"
        self.temp_state: Optional[str] = None
        self.temp_state_timer = 0
        self.facing_left = False

        # Smooth cross-fade transition between states
        self.prev_pixmap: Optional[QPixmap] = None
        self.transition_progress = 1.0  # 1.0 means no transition, 0.0 means starting

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
        self.squash_factor = 1.0

        # Walking step animation
        self.walk_step_phase = 0.0

        # Carried file rendering and throwing arc
        self.carried_file_name: str = ""
        self.throw_arc_progress: float = -1.0  # -1 means not throwing, 0.0 to 1.0 while throwing

        # Particles
        self.particles: List[Particle] = []

        # 60 FPS update timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(16)

    def _load_assets(self):
        """Map canonical states to authentic Whale Musume WebP assets."""
        asset_files = {
            # Base Idle & Movement
            "idle": "idle-cute.webp",
            "tail_swing": "tail-swing.webp",
            "wink": "wink.webp",
            "running": "running.webp",
            "pickup": "pick-up.webp",
            "waiting": "waiting.webp",
            "curious": "curious.webp",
            "stretch": "daily-stretch.webp",
            "sleep": "sleep.webp",
            "afk": "afk.webp",

            # Thinking & Work
            "thinking": "thinking.webp",
            "doubt": "meme-doubt.webp",
            "review": "work-review.webp",
            "debug": "work-debug.webp",
            "deploy": "work-deploy.webp",
            "slack": "work-slack.webp",

            # Celebrations & Emotions
            "happy": "celebrate.webp",
            "celebrate": "work-celebrate.webp",
            "game_happy": "game-happy.webp",
            "success": "success.webp",
            "failure": "failure.webp",
            "cry": "meme-cry.webp",
            "smug": "meme-smug.webp",
            "wakuwaku": "meme-wakuwaku.webp",
            "kyun": "meme-kyun.webp",

            # Interactions
            "headpat": "react-head.webp",
            "feed": "daily-eat.webp",
            "belly": "react-belly.webp",
            "tail": "react-tail.webp",

            # Daily Life & Trash mission
            "cooking": "daily-cooking.webp",
            "picnic": "daily-picnic.webp",
            "sweep": "sweep.webp",
            "tool": "tool.webp"
        }

        for key, fname in asset_files.items():
            p = resolve_asset_path(fname)
            if p.exists():
                pix = QPixmap(str(p))
                if not pix.isNull():
                    self.pixmaps[key] = pix
                    img = pix.toImage().mirrored(True, False)
                    self.mirrored_pixmaps[key] = QPixmap.fromImage(img)

    def set_scale(self, scale: float):
        self.scale_factor = max(0.5, min(2.5, scale))
        w = int(self.base_width * self.scale_factor)
        h = int(self.base_height * self.scale_factor)
        self.setFixedSize(w, h)
        self.update()

    def set_facing(self, facing_left: bool):
        """Set horizontal facing direction for walking or running."""
        if self.facing_left != facing_left:
            self.facing_left = facing_left
            self.update()

    def set_state(self, state: str, temp_duration_ms: int = 0):
        alias_map = {
            "studying": "reading",
            "resting": "sleep",
            "eat": "feed",
            "yawn": "stretch",
            "walk": "walking_right",
            "jump": "jumping",
            "excited": "happy",
            "observing": "watching",
            "code": "computer",
            # File recycle aliases
            "receive_file": "curious",
            "carry_file": "pickup",
            "run_with_file": "running",
            "arrive_recycle_bin": "waiting",
            "throw_file": "deploy",
            "delete_success": "celebrate",
            "delete_failed": "cry",
            "return_home": "running"
        }
        target_state = alias_map.get(state, state)

        # Trigger smooth crossfade if changing state
        active_before = self.temp_state or self.current_state
        if active_before != target_state and self.transition_progress >= 0.8:
            pix_curr, _ = self._get_active_pixmap()
            self.prev_pixmap = pix_curr
            self.transition_progress = 0.0

        if temp_duration_ms > 0:
            self.temp_state = target_state
            self.temp_state_timer = int(temp_duration_ms / 16)
        else:
            self.current_state = target_state
            self.temp_state = None

        self._spawn_state_particles(target_state)
        self.state_changed.emit(target_state)
        self.update()

    def set_carried_file(self, filename: str):
        """Set carried file name to render a cute document badge."""
        self.carried_file_name = filename
        self.update()

    def start_throw_animation(self):
        """Trigger throwing parabolic arc animation for carried file."""
        self.throw_arc_progress = 0.0

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

    def _spawn_state_particles(self, state: str):
        cx = self.width() / 2
        cy = self.height() / 2

        if state in ["happy", "celebrate", "delete_success"]:
            for _ in range(8):
                p = Particle(
                    p_type="star",
                    x=cx + random.uniform(-40, 40),
                    y=cy - 30 + random.uniform(-20, 20),
                    vx=random.uniform(-1.8, 1.8),
                    vy=random.uniform(-2.8, -0.6),
                    max_life=50,
                    color=random.choice([QColor(255, 215, 0), QColor(255, 140, 0), QColor(100, 220, 255)])
                )
                self.particles.append(p)
        elif state == "headpat":
            for _ in range(6):
                p = Particle(
                    p_type="heart",
                    x=cx + random.uniform(-30, 30),
                    y=cy - 60 + random.uniform(-10, 10),
                    vx=random.uniform(-1.2, 1.2),
                    vy=random.uniform(-2.2, -0.8),
                    max_life=55,
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
        elif state in ["cry", "failure", "delete_failed"]:
            for _ in range(5):
                p = Particle(
                    p_type="tear",
                    x=cx + random.choice([-15, 15]),
                    y=cy - 20,
                    vx=random.uniform(-0.3, 0.3),
                    vy=random.uniform(1.2, 2.8),
                    max_life=45,
                    color=QColor(100, 180, 255)
                )
                self.particles.append(p)

    def _on_tick(self):
        self.anim_tick += 1

        # Smooth cross-fade transition step
        if self.transition_progress < 1.0:
            self.transition_progress = min(1.0, self.transition_progress + 0.12)

        # Handle temporary state countdown
        if self.temp_state is not None:
            self.temp_state_timer -= 1
            if self.temp_state_timer <= 0:
                self.temp_state = None
                self.state_changed.emit(self.current_state)

        active = self.temp_state or self.current_state

        # Natural blinking logic
        self.blink_tick += 1
        if self.blink_tick > 220 + (self.anim_tick % 90):
            self.is_blinking = True
            if self.blink_tick > 228 + (self.anim_tick % 90):
                self.is_blinking = False
                self.blink_tick = 0

        # Tail wagging cycle
        self.tail_wag_tick += 1
        if self.tail_wag_tick > 190:
            self.is_tail_wagging = True
            if self.tail_wag_tick > 218:
                self.is_tail_wagging = False
                self.tail_wag_tick = 0

        # Walking step phase
        if active in ["walking_left", "walking_right", "running"]:
            self.walk_step_phase += 0.28

        # Throwing arc progress
        if self.throw_arc_progress >= 0.0:
            self.throw_arc_progress += 0.05
            if self.throw_arc_progress > 1.0:
                self.throw_arc_progress = -1.0
                self.carried_file_name = ""

        # Physics simulation for jump / drop
        if self.is_in_physics:
            self.vel_y += self.gravity
            self.pos_y_offset += self.vel_y
            if self.pos_y_offset >= 0:
                self.pos_y_offset = 0
                if abs(self.vel_y) > 2.5 and self.bounce_count < 3:
                    self.vel_y = -self.vel_y * self.bounce_damping
                    self.bounce_count += 1
                    self.squash_factor = 0.88
                else:
                    self.vel_y = 0
                    self.is_in_physics = False
                    self.squash_factor = 1.0
                    if active in ["jumping", "falling"]:
                        self.set_state("idle")
        else:
            if self.squash_factor < 1.0:
                self.squash_factor = min(1.0, self.squash_factor + 0.04)

        # Update particles
        alive_particles = []
        for p in self.particles:
            p.update()
            if p.is_alive:
                alive_particles.append(p)
        self.particles = alive_particles

        if active in ["sleep", "resting"] and self.anim_tick % 70 == 0:
            self._spawn_state_particles("sleep")

        self.update()

    def _get_active_pixmap(self) -> Tuple[Optional[QPixmap], bool]:
        active = self.temp_state or self.current_state
        flip = self.facing_left
        pix_dict = self.mirrored_pixmaps if flip else self.pixmaps

        if active == "walking_left":
            return self.mirrored_pixmaps.get("running") or self.pixmaps.get("idle"), True
        elif active in ["walking_right", "running"]:
            return pix_dict.get("running") or pix_dict.get("idle"), flip
        elif active in ["jumping", "drag", "falling", "pickup"]:
            return pix_dict.get("pickup") or pix_dict.get("happy"), flip
        elif active == "thinking":
            return pix_dict.get("thinking") or pix_dict.get("idle"), flip
        elif active in ["confused", "doubt"]:
            return pix_dict.get("doubt") or pix_dict.get("idle"), flip
        elif active in ["happy", "celebrate"]:
            return pix_dict.get("celebrate") or pix_dict.get("happy") or pix_dict.get("idle"), flip
        elif active in ["cry", "failure"]:
            return pix_dict.get("cry") or pix_dict.get("idle"), flip
        elif active in ["smug", "proud"]:
            return pix_dict.get("smug") or pix_dict.get("idle"), flip
        elif active in ["reading", "review"]:
            return pix_dict.get("review") or pix_dict.get("idle"), flip
        elif active in ["computer", "debug"]:
            return pix_dict.get("debug") or pix_dict.get("idle"), flip
        elif active == "deploy":
            return pix_dict.get("deploy") or pix_dict.get("review") or pix_dict.get("idle"), flip
        elif active == "sweep":
            return pix_dict.get("sweep") or pix_dict.get("idle"), flip
        elif active in ["watching", "waiting"]:
            return pix_dict.get("curious") or pix_dict.get("waiting") or pix_dict.get("idle"), flip
        elif active in ["stretch", "yawn"]:
            return pix_dict.get("stretch") or pix_dict.get("idle"), flip
        elif active in ["sleep", "resting"]:
            return pix_dict.get("sleep") or pix_dict.get("idle"), flip
        elif active == "headpat":
            return pix_dict.get("headpat") or pix_dict.get("idle"), flip
        elif active in ["feed", "eat"]:
            return pix_dict.get("feed") or pix_dict.get("idle"), flip
        elif active == "touch_belly":
            return pix_dict.get("belly") or pix_dict.get("idle"), flip
        elif active == "touch_tail":
            return pix_dict.get("tail") or pix_dict.get("idle"), flip
        elif active == "afk":
            return pix_dict.get("afk") or pix_dict.get("idle"), flip

        # Idle baseline with blink and tail wagging
        if self.is_blinking and "wink" in pix_dict:
            return pix_dict["wink"], flip
        if self.is_tail_wagging and "tail_swing" in pix_dict:
            return pix_dict["tail_swing"], flip

        return pix_dict.get("idle"), flip

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
            breath_y = math.sin(self.anim_tick * 0.05) * 2.2
            breath_scale = 1.0 + math.sin(self.anim_tick * 0.05) * 0.015

        # 2. Walk step bobbing offset
        walk_y = 0.0
        if active in ["walking_left", "walking_right", "running"]:
            walk_y = abs(math.sin(self.walk_step_phase)) * -5.5

        # 3. Physics vertical offset (jumping/falling)
        physics_y = self.pos_y_offset

        # 4. Total vertical displacement
        total_offset_y = breath_y + walk_y + physics_y

        pad_x = 10 * self.scale_factor
        pad_top = 15 * self.scale_factor
        draw_w = w - pad_x * 2
        draw_h = h - pad_top - (10 * self.scale_factor)

        sy = self.squash_factor * breath_scale
        sx = (2.0 - sy)

        center_x = w / 2
        base_y = h - (12 * self.scale_factor) + total_offset_y

        # Draw character with cross-fade if transitioning
        dest_rect = QRectF(-draw_w / 2, -draw_h, draw_w, draw_h)

        painter.save()
        painter.translate(center_x, base_y)
        painter.scale(sx, sy)

        if self.transition_progress < 1.0 and self.prev_pixmap and not self.prev_pixmap.isNull():
            # Draw blended previous sprite
            painter.setOpacity(1.0 - self.transition_progress)
            painter.drawPixmap(dest_rect, self.prev_pixmap, QRectF(self.prev_pixmap.rect()))
            painter.setOpacity(self.transition_progress)
            painter.drawPixmap(dest_rect, pix, QRectF(pix.rect()))
        else:
            painter.drawPixmap(dest_rect, pix, QRectF(pix.rect()))

        painter.restore()

        # 5. Render carried file or throwing parabolic arc
        if self.carried_file_name:
            self._draw_carried_file(painter, center_x, base_y - draw_h * 0.45)

        # 6. Render Particle System
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

    def _draw_carried_file(self, painter: QPainter, base_x: float, base_y: float):
        """Draw cute miniature document icon carried by Whale Musume."""
        painter.save()

        fx = base_x + (15 if not self.facing_left else -35)
        fy = base_y

        # Handle parabolic throw animation
        if self.throw_arc_progress >= 0.0:
            t = self.throw_arc_progress
            # Arc towards top left / into bin
            fx = base_x + (t * -70.0 if self.facing_left else t * 70.0)
            # Parabolic height: h = -4 * max_h * t * (t - 1)
            arc_y = -60.0 * 4.0 * t * (1.0 - t)
            fy = base_y + arc_y + (t * 40.0)
            painter.setOpacity(max(0.0, 1.0 - t * 0.8))

        # Miniature document sheet (white rounded rect with folded corner)
        fw = 32 * self.scale_factor
        fh = 40 * self.scale_factor

        painter.setPen(QPen(QColor(70, 90, 140, 200), 1.5))
        painter.setBrush(QBrush(QColor(255, 255, 255, 240)))
        painter.drawRoundedRect(QRectF(fx, fy, fw, fh), 4, 4)

        # Lines on paper
        painter.setPen(QPen(QColor(180, 200, 230), 1.5))
        painter.drawLine(QPointF(fx + 6, fy + 12), QPointF(fx + fw - 6, fy + 12))
        painter.drawLine(QPointF(fx + 6, fy + 20), QPointF(fx + fw - 6, fy + 20))
        painter.drawLine(QPointF(fx + 6, fy + 28), QPointF(fx + fw - 12, fy + 28))

        # Cute trash tag badge
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(239, 68, 68, 220)))
        painter.drawRoundedRect(QRectF(fx + fw - 16, fy - 4, 18, 12), 3, 3)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", int(7 * self.scale_factor), QFont.Weight.Bold))
        painter.drawText(QRectF(fx + fw - 16, fy - 4, 18, 12), Qt.AlignmentFlag.AlignCenter, "DEL")

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
        w = self.width()
        h = self.height()
        rel_x = local_x / w
        rel_y = local_y / h

        if 0.25 <= rel_x <= 0.75 and 0.08 <= rel_y <= 0.38:
            return "head"
        elif 0.32 <= rel_x <= 0.68 and 0.40 <= rel_y <= 0.68:
            return "belly"
        elif rel_x > 0.65 and rel_y > 0.45:
            return "tail"
        return "body"

    def dragEnterEvent(self, event):
        p = self.parent()
        if p and hasattr(p, "dragEnterEvent"):
            p.dragEnterEvent(event)
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        p = self.parent()
        if p and hasattr(p, "dragMoveEvent"):
            p.dragMoveEvent(event)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        p = self.parent()
        if p and hasattr(p, "dragLeaveEvent"):
            p.dragLeaveEvent(event)
        else:
            event.accept()

    def dropEvent(self, event):
        p = self.parent()
        if p and hasattr(p, "dropEvent"):
            p.dropEvent(event)
        else:
            event.ignore()

