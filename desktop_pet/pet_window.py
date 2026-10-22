from __future__ import annotations
import ctypes
import os
import sys
import time
import math
import webbrowser
import threading
import httpx
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QPoint, QTimer, QSize, Signal, QObject
from PySide6.QtGui import QAction, QCursor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QMenu, QApplication,
    QSystemTrayIcon, QFileDialog
)

from desktop_pet.fish_renderer import FishRenderer, resolve_asset_path
from desktop_pet.speech_bubble import SpeechBubble
from desktop_pet.chat_dialog import ChatDialog
from desktop_pet.virtual_bin_marker import VirtualRecycleBinMarker
from desktop_pet.recycle_bin_helper import (
    is_safe_to_recycle, recycle_file, find_desktop_recycle_bin_pos,
    enable_windows_drag_drop_privilege
)

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000


def set_click_through(hwnd: int, enabled: bool):
    """Enable or disable mouse click-through for transparent overlay window."""
    if sys.platform != "win32":
        return
    try:
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if enabled:
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT | WS_EX_LAYERED)
        else:
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style & ~WS_EX_TRANSPARENT)
    except Exception as e:
        print(f"[PetWindow] Click-through set failed: {e}")


class PetSignals(QObject):
    """Thread-safe Qt signal bridge for async backend communication."""
    status_synced = Signal(dict)
    explore_finished = Signal(dict)
    explore_failed = Signal()


class PetWindow(QWidget):
    """
    Main transparent desktop pet window for '大肥鱼' (Whale Musume).
    Supports high-res DeepSeek character animations, drag-and-drop rebound physics,
    interactive file trash carrying & recycling mission across real Windows desktop,
    click-through, scaling, multi-monitor geometry, and tray controls.
    """

    def __init__(self, backend_url="http://127.0.0.1:8000"):
        super().__init__()
        self.backend_url = backend_url
        self.drag_position = QPoint()
        self.drag_start_time = 0.0
        self.is_dragging = False
        self.is_click_through = False

        # Thread-safe signals
        self.signals = PetSignals()
        self.signals.status_synced.connect(self._on_status_synced)
        self.signals.explore_finished.connect(self._on_explore_finished)
        self.signals.explore_failed.connect(self._on_explore_failed)

        # Frameless, transparent, always on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Enable dragging files onto the pet
        self.setAcceptDrops(True)
        self.recycle_without_confirm = False
        try:
            enable_windows_drag_drop_privilege(int(self.winId()))
        except Exception:
            pass

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Authentic Whale Musume Renderer
        self.renderer = FishRenderer(self)
        self.layout.addWidget(self.renderer)

        # Scale Factor (1.0 default = 250x270)
        self.current_scale = 1.0

        # Initial Position (bottom right of primary screen, above taskbar)
        self._init_position()

        # Chat dialog
        self.chat_dialog = ChatDialog(
            backend_url=self.backend_url,
            parent=None,
            on_state_change=self.renderer.set_state
        )

        # Speech bubble
        self.bubble = SpeechBubble(
            parent=None,
            on_chat_clicked=self._open_chat
        )

        # Virtual Recycle Bin Marker (displayed during file mission)
        self.bin_marker = VirtualRecycleBinMarker(parent=None)

        # State and sync
        self.current_mood = "探索兴起"
        self.current_bubble_text = "今天有什么新奇事物在等着我们呢？咕噜噜~"

        # Recycle mission state variables
        self.is_in_recycle_mission = False
        self.home_pos = QPoint()
        self.target_pos = QPoint()
        self.mission_file_path = ""
        self.move_timer = QTimer(self)
        self.move_timer.timeout.connect(self._on_move_tick)
        self.move_speed = 9.0  # pixels per frame at 60 FPS (~540px/s)
        self.mission_phase = "idle"  # 'running_to_bin', 'returning_home'

        # System tray icon setup
        self._init_tray_icon()

        # Polling timer for backend sync
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self._sync_backend_status)
        self.sync_timer.start(5000)

        # Initial bubble popup
        QTimer.singleShot(1500, self._show_bubble)

    def _init_position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        init_x = screen.x() + screen.width() - self.renderer.width() - 40
        init_y = screen.y() + screen.height() - self.renderer.height() - 20
        self.move(init_x, init_y)

    def _init_tray_icon(self):
        icon_path = resolve_asset_path("idle-cute.webp")
        if icon_path.exists():
            pix = QPixmap(str(icon_path)).scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            tray_icon = QIcon(pix)
        else:
            tray_icon = QIcon()

        self.tray = QSystemTrayIcon(tray_icon, self)
        self.tray.setToolTip("大肥鱼的B站生活 - 桌宠小鲸鱼")

        menu = QMenu()
        self._build_context_menu(menu)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.is_click_through:
                self.toggle_click_through(False)
            self.show()
            self.raise_()
            self.activateWindow()

    def set_pet_scale(self, scale: float):
        self.current_scale = scale
        self.renderer.set_scale(scale)
        self.adjustSize()
        if self.bubble.isVisible():
            self._update_bubble_position()

    def toggle_click_through(self, enabled: bool):
        self.is_click_through = enabled
        set_click_through(self.winId(), enabled)
        if enabled:
            self.tray.showMessage(
                "大肥鱼 - 鼠标穿透已开启",
                "小肥鱼现在不会阻挡鼠标点击。如需恢复交互，请在系统托盘右键关闭穿透或双击托盘图标。",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )

    def _sync_backend_status(self):
        if self.is_in_recycle_mission:
            return  # Do not interrupt active file delivery mission

        def _fetch():
            try:
                res = httpx.get(f"{self.backend_url}/api/pet/status", timeout=2.5)
                if res.status_code == 200:
                    self.signals.status_synced.emit(res.json())
            except Exception:
                pass

        threading.Thread(target=_fetch, daemon=True).start()

    def _on_status_synced(self, data: dict):
        """Thread-safe UI update slot for backend status."""
        if self.is_in_recycle_mission:
            return
        new_state = data.get("state", "idle")
        new_mood = data.get("mood", "探索兴起")
        new_bubble = data.get("bubble_text", "")

        self.current_mood = new_mood
        if new_bubble:
            self.current_bubble_text = new_bubble
        self.renderer.set_state(new_state)

    def _update_bubble_position(self):
        pos = self.mapToGlobal(QPoint(0, 0))
        bx = pos.x() + (self.width() - self.bubble.width()) // 2
        by = pos.y() - self.bubble.height() - 10
        if by < 10:
            by = pos.y() + self.height() + 10
        self.bubble.move(bx, by)

    def _show_bubble(self):
        self._update_bubble_position()
        self.bubble.show_message(self.current_mood, self.current_bubble_text, duration_ms=6000)

    def _open_chat(self):
        self.bubble.hide()
        self.chat_dialog.show()
        self.chat_dialog.raise_()
        self.chat_dialog.activateWindow()

    def _explore(self):
        if self.is_in_recycle_mission:
            return
        self.renderer.set_state("thinking")
        self.bubble.show_message("正在探索", "大肥鱼正游出水缸，去B站看看有什么新奇的科学与创意视频...", duration_ms=4000)

        def _do_explore():
            try:
                res = httpx.post(f"{self.backend_url}/api/discovery/explore", timeout=15.0)
                if res.status_code == 200:
                    candidates = res.json()
                    self.signals.explore_finished.emit(candidates[0] if candidates else {})
                else:
                    self.signals.explore_failed.emit()
            except Exception:
                self.signals.explore_failed.emit()

        threading.Thread(target=_do_explore, daemon=True).start()

    def _on_explore_finished(self, first_candidate: dict):
        if first_candidate:
            self.renderer.set_state("happy")
            self.current_mood = "大开眼界"
            self.current_bubble_text = f"发现新视频：《{first_candidate.get('title', '')[:15]}...》！{first_candidate.get('reason', '')}"
            self._show_bubble()
        else:
            self.renderer.set_state("idle")

    def _on_explore_failed(self):
        self.renderer.set_state("confused")

    # --- Windows Drag & Drop File Reception ---

    def dragEnterEvent(self, event):
        if self.is_in_recycle_mission or self.is_click_through:
            event.ignore()
            return

        if event.mimeData().hasUrls():
            urls = [u for u in event.mimeData().urls() if u.isLocalFile()]
            if urls:
                self.renderer.set_state("receive_file")
                self._update_bubble_position()
                self.bubble.show_message("发现文件", "哇！主人交给我什么啦？松开鼠标交给我看看~", duration_ms=3000)
                event.acceptProposedAction()
                return
        event.ignore()

    def dragMoveEvent(self, event):
        if self.is_in_recycle_mission or self.is_click_through:
            event.ignore()
            return

        if event.mimeData().hasUrls():
            urls = [u for u in event.mimeData().urls() if u.isLocalFile()]
            if urls:
                event.acceptProposedAction()
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        if not self.is_in_recycle_mission:
            self.renderer.set_state("idle")
            self.bubble.hide()
        event.accept()

    def dropEvent(self, event):
        if self.is_in_recycle_mission or self.is_click_through:
            event.ignore()
            return

        urls = [u for u in event.mimeData().urls() if u.isLocalFile()]
        if not urls:
            event.ignore()
            return

        event.acceptProposedAction()
        raw_path = urls[0].toLocalFile().strip('"\'' )
        local_path = os.path.normpath(raw_path)
        self._handle_file_dropped(local_path)

    def _handle_file_dropped(self, file_path: str):
        """Process dropped file: perform safety checks and present confirmation dialog."""
        safe, reason = is_safe_to_recycle(file_path)
        if not safe:
            self.renderer.set_state("doubt", temp_duration_ms=4000)
            self._update_bubble_position()
            self.bubble.show_message("安全防护", f"主人，这个文件不能丢进垃圾桶哦：{reason}", duration_ms=4500)
            return

        p = Path(file_path)
        file_name = p.name
        try:
            size_bytes = os.path.getsize(file_path)
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        except Exception:
            size_str = "大小未知"

        # Check direct recycle mode
        if getattr(self, "recycle_without_confirm", False):
            self._start_recycle_mission(file_path)
            return

        self.renderer.set_state("receive_file")
        self._update_bubble_position()
        self.bubble.show_recycle_confirm(
            file_name=file_name,
            size_str=size_str,
            on_confirm=lambda: self._start_recycle_mission(file_path),
            on_cancel=self._cancel_recycle_mission
        )

    def _cancel_recycle_mission(self):
        self.renderer.set_state("happy", temp_duration_ms=2500)
        self._update_bubble_position()
        self.bubble.show_message("文件保留", "好哒！文件已经帮你安全留在原处啦~ ✨", duration_ms=3000)

    # --- Real Screen Movement & Recycle Bin Delivery Mission ---

    def _start_recycle_mission(self, file_path: str):
        self.is_in_recycle_mission = True
        self.mission_file_path = file_path
        self.home_pos = self.pos()

        # Detect Recycle Bin target position
        bin_x, bin_y, is_virtual = find_desktop_recycle_bin_pos()
        # Offset target so pet stands comfortably beside the bin
        dest_x = bin_x + 60
        dest_y = bin_y + 10
        self.target_pos = QPoint(dest_x, dest_y)

        # Show virtual bin marker if needed
        self.bin_marker.show_at(bin_x, bin_y)

        # Setup character carrying file
        file_name = Path(file_path).name
        self.renderer.set_carried_file(file_name)
        self.renderer.set_state("run_with_file")
        self._update_bubble_position()
        self.bubble.show_message("全力奔跑", f"呼哧呼哧~ 抱紧【{file_name[:12]}】，正在跑向回收站！", duration_ms=3000)

        # Start 60 FPS motion loop
        self.mission_phase = "running_to_bin"
        self.move_timer.start(16)

    def _on_move_tick(self):
        curr_x = float(self.x())
        curr_y = float(self.y())

        dest = self.target_pos if self.mission_phase == "running_to_bin" else self.home_pos
        dx = float(dest.x()) - curr_x
        dy = float(dest.y()) - curr_y
        dist = math.hypot(dx, dy)

        if dist <= self.move_speed:
            # Arrived at destination
            self.move(dest)
            if self.mission_phase == "running_to_bin":
                self.move_timer.stop()
                self._on_arrived_at_bin()
            elif self.mission_phase == "returning_home":
                self.move_timer.stop()
                self._on_returned_home()
            return

        # Move one step towards destination
        step_x = (dx / dist) * self.move_speed
        step_y = (dy / dist) * self.move_speed
        new_pos = QPoint(int(curr_x + step_x), int(curr_y + step_y))
        self.move(new_pos)

        # Update facing direction (flip sprite if moving left)
        self.renderer.set_facing(step_x < 0)

        # Keep speech bubble tracking pet
        if self.bubble.isVisible():
            self._update_bubble_position()

    def _on_arrived_at_bin(self):
        """Arrived at the Recycle Bin: trigger throwing animation and real deletion."""
        self.renderer.set_state("throw_file")
        self.renderer.start_throw_animation()
        self._update_bubble_position()
        self.bubble.show_message("正在投递", "呀嘿！把垃圾文件投进回收站桶里~ 🗑️", duration_ms=2000)

        def _execute_delete():
            success, msg = recycle_file(self.mission_file_path)
            if success:
                self.renderer.set_state("delete_success")
                self._update_bubble_position()
                self.bubble.show_message("投递成功", "🎉 啪嗒！文件已安全送入 Windows 回收站，桌面又干干净净啦！", duration_ms=3500)
            else:
                self.renderer.set_state("delete_failed")
                self._update_bubble_position()
                self.bubble.show_message("操作遇到阻碍", f"呜呜，丢不掉：{msg}", duration_ms=3500)

            # Wait 1.6s for celebration/reaction, then run back home
            QTimer.singleShot(1600, self._start_return_home)

        QTimer.singleShot(600, _execute_delete)

    def _start_return_home(self):
        """Turn around and run back across the desktop to original starting location."""
        self.mission_phase = "returning_home"
        self.renderer.set_state("return_home")
        self.renderer.set_facing(self.home_pos.x() < self.x())
        self._update_bubble_position()
        self.bubble.show_message("正在归位", "任务完成！小肥鱼正在快步跑回原来的休息位置~ 🐬", duration_ms=2500)
        self.move_timer.start(16)

    def _on_returned_home(self):
        """Safely back home: resume normal idle breathing and tail wagging."""
        self.is_in_recycle_mission = False
        self.renderer.set_facing(False)
        self.renderer.set_state("idle")
        self.bin_marker.dismiss()
        self._update_bubble_position()
        self.bubble.show_message("平安归来", "咕噜噜~ 顺利回家！主人还有什么需要帮忙的吗？✨", duration_ms=4000)

    # --- Mouse Events for Dragging, Rebound and Interactions ---

    def mousePressEvent(self, event):
        if self.is_in_recycle_mission or self.is_click_through:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.drag_start_time = time.time()
            self.is_dragging = True
            self.renderer.set_state("drag")
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_in_recycle_mission or self.is_click_through:
            return
        if event.buttons() == Qt.MouseButton.LeftButton and self.is_dragging:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            if self.bubble.isVisible():
                self._update_bubble_position()
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.is_in_recycle_mission or self.is_click_through:
            return
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            duration = time.time() - self.drag_start_time

            if duration < 0.25:
                click_pos = event.position()
                region = self.renderer.hit_test_region(click_pos.x(), click_pos.y())

                if region == "head":
                    self.renderer.set_state("headpat", temp_duration_ms=3500)
                    self._update_bubble_position()
                    self.bubble.show_message("心动摸头", "摸摸头~ 咕噜噜！小肥鱼的呆毛蹭了蹭你的手心，充满电啦！✨", duration_ms=4000)
                elif region == "belly":
                    self.renderer.set_state("touch_belly", temp_duration_ms=3000)
                    self._update_bubble_position()
                    self.bubble.show_message("好痒痒~", "噗嗤！别挠肚皮啦，小鲸鱼要笑翻到桌子底下去啦！(>▽<)", duration_ms=3500)
                elif region == "tail":
                    self.renderer.set_state("touch_tail", temp_duration_ms=3000)
                    self._update_bubble_position()
                    self.bubble.show_message("羞羞护尾", "哇呀！尾巴是敏感区，不能随便揪的啦~ 摇两下抗议！(脸红)", duration_ms=3500)
                else:
                    self._show_bubble()
            else:
                self.renderer.trigger_drop_rebound()
                screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
                avail_bottom = screen.availableGeometry().bottom()
                if self.geometry().bottom() > avail_bottom:
                    self.move(self.x(), avail_bottom - self.height())

            event.accept()

    def contextMenuEvent(self, event):
        if self.is_click_through or self.is_in_recycle_mission:
            return
        menu = QMenu(self)
        self._build_context_menu(menu)
        menu.exec(QCursor.pos())

    def _demo_recycle_feature(self):
        """Create a temporary test file and demonstrate the complete recycle bin mission."""
        import tempfile
        try:
            with tempfile.NamedTemporaryFile(delete=False, prefix="whale_test_trash_", suffix=".txt") as tf:
                tf.write(b"DeepSeek Whale Musume Trash Recycle Feature Test File.")
                tf_path = tf.name
            self._handle_file_dropped(tf_path)
        except Exception as e:
            self.bubble.show_message("测试提示", f"创建临时演示文件失败: {e}", 3000)

    def _toggle_recycle_confirm(self):
        self.recycle_without_confirm = not getattr(self, "recycle_without_confirm", False)
        mode_desc = "拖入直接丢进回收站（无需二次点击）" if self.recycle_without_confirm else "二次弹窗确认（点击按钮后再送去回收站）"
        self._update_bubble_position()
        self.bubble.show_message("模式切换", f"丢垃圾已设为：{mode_desc}", duration_ms=3500)


    def _build_context_menu(self, menu: QMenu):
        menu.setStyleSheet("""
            QMenu {
                background: #ffffff;
                border: 1px solid #cbd5e0;
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 22px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #ebf8ff;
                color: #2b6cb0;
            }
            QMenu::separator {
                height: 1px;
                background: #e2e8f0;
                margin: 4px 8px;
            }
        """)

        # Action: Chat
        chat_act = QAction("💬 找我聊天", self)
        chat_act.triggered.connect(self._open_chat)
        menu.addAction(chat_act)

        # Action: Explore
        explore_act = QAction("🧭 出去逛逛 (探索新视频)", self)
        explore_act.triggered.connect(self._explore)
        menu.addAction(explore_act)

        # Action: Trash Recycle Demo
        trash_act = QAction("🗑️ 帮我丢垃圾 (功能演示)", self)
        trash_act.triggered.connect(self._demo_recycle_feature)
        menu.addAction(trash_act)

        # Action: Toggle Recycle Confirmation
        confirm_text = "开启确认弹窗 (防误触)" if not getattr(self, "recycle_without_confirm", False) else "关闭确认弹窗 (拖入直接丢)"
        confirm_mode_act = QAction(f"⚙️ 丢垃圾模式: {confirm_text}", self)
        confirm_mode_act.triggered.connect(self._toggle_recycle_confirm)
        menu.addAction(confirm_mode_act)

        # Interaction Submenu
        interact_menu = menu.addMenu("✨ 宠溺互动")
        head_act = QAction("🥰 摸摸鱼头", self)
        head_act.triggered.connect(lambda: [self.renderer.set_state("headpat", 3500), self.bubble.show_message("心动摸头", "摸摸头~ 咕噜噜！小肥鱼的呆毛蹭了蹭你的手心，充满电啦！✨", 4000)])
        feed_act = QAction("🍪 投喂小饼干", self)
        feed_act.triggered.connect(lambda: [self.renderer.set_state("feed", 3500), self.bubble.show_message("美味点心", "咔嚓咔嚓~ 磷虾风味小饼干真好吃！谢谢主人投喂！(嚼嚼嚼)", 4000)])
        belly_act = QAction("🐱 戳戳小肚皮", self)
        belly_act.triggered.connect(lambda: [self.renderer.set_state("touch_belly", 3000), self.bubble.show_message("痒痒笑", "别挠啦主人，小肥鱼要笑得游不动啦！(>▽<)", 3500)])
        tail_act = QAction("🐬 轻碰鲸鱼尾", self)
        tail_act.triggered.connect(lambda: [self.renderer.set_state("touch_tail", 3000), self.bubble.show_message("羞羞护尾", "尾巴左右摆动了一下，表示害羞与亲近~", 3500)])
        jump_act = QAction("🦘 活力跳跃", self)
        jump_act.triggered.connect(self.renderer.trigger_jump)
        for a in [head_act, feed_act, belly_act, tail_act, jump_act]:
            interact_menu.addAction(a)

        menu.addSeparator()

        # Full Animation Suite Submenu (Covers all required states)
        anim_menu = menu.addMenu("🎭 动作测试 / 状态演示")
        all_actions = [
            ("🌊 待机呼吸 (Idle)", "idle"),
            ("🏃 左右走动 (Walk / Run)", "running"),
            ("🦘 活力跳跃 (Jump)", "jumping"),
            ("💭 吐泡思考 (Thinking)", "thinking"),
            ("❓ 歪头疑惑 (Confused)", "confused"),
            ("🌟 欢呼开心 (Happy)", "happy"),
            ("🎉 任务庆祝 (Celebrate)", "celebrate"),
            ("😭 扁嘴委屈 (Aggrieved)", "cry"),
            ("😎 得意叉腰 (Proud)", "smug"),
            ("📖 专注读书 (Reading)", "reading"),
            ("💻 编写代码 (Computer)", "computer"),
            ("🙆 伸个懒腰 (Stretch)", "stretch"),
            ("💤 呼呼大睡 (Sleep)", "sleep"),
            ("🎮 挂机休眠 (AFK)", "afk"),
        ]
        for name, key in all_actions:
            act = QAction(name, self)
            if key == "jumping":
                act.triggered.connect(self.renderer.trigger_jump)
            else:
                act.triggered.connect(lambda checked=False, k=key: self.renderer.set_state(k))
            anim_menu.addAction(act)

        # Scale Submenu
        scale_menu = menu.addMenu("🔍 尺寸缩放")
        scales = [
            ("小巧 (0.75x)", 0.75),
            ("标准 (1.0x)", 1.0),
            ("清晰 (1.25x)", 1.25),
            ("醒目 (1.5x)", 1.5),
        ]
        for s_name, s_val in scales:
            s_act = QAction(s_name, self)
            s_act.setCheckable(True)
            s_act.setChecked(abs(self.current_scale - s_val) < 0.05)
            s_act.triggered.connect(lambda checked=False, val=s_val: self.set_pet_scale(val))
            scale_menu.addAction(s_act)

        menu.addSeparator()

        # Action: Open Dashboard
        dashboard_act = QAction("🌐 打开管理面板", self)
        dashboard_act.triggered.connect(lambda: webbrowser.open("http://127.0.0.1:8000"))
        menu.addAction(dashboard_act)

        # Action: Click-Through Toggle
        ct_act = QAction("👻 鼠标穿透 (点击穿透)", self)
        ct_act.setCheckable(True)
        ct_act.setChecked(self.is_click_through)
        ct_act.triggered.connect(lambda checked: self.toggle_click_through(checked))
        menu.addAction(ct_act)

        # Action: Toggle Always on Top
        top_act = QAction("📌 窗口置顶", self)
        top_act.setCheckable(True)
        top_act.setChecked(bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint))
        top_act.triggered.connect(self._toggle_always_on_top)
        menu.addAction(top_act)

        menu.addSeparator()

        # Action: Exit
        exit_act = QAction("❌ 退出小肥鱼", self)
        exit_act.triggered.connect(QApplication.instance().quit)
        menu.addAction(exit_act)

    def _toggle_always_on_top(self):
        flags = self.windowFlags()
        if flags & Qt.WindowType.WindowStaysOnTopHint:
            self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        self.show()
