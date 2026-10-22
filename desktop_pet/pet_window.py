from __future__ import annotations
import ctypes
import sys
import time
import webbrowser
import threading
import httpx
from PySide6.QtCore import Qt, QPoint, QTimer, QSize
from PySide6.QtGui import QAction, QCursor, QIcon, QPixmap
from PySide6.QtWidgets import QWidget, QVBoxLayout, QMenu, QApplication, QSystemTrayIcon

from desktop_pet.fish_renderer import FishRenderer, resolve_asset_path
from desktop_pet.speech_bubble import SpeechBubble
from desktop_pet.chat_dialog import ChatDialog

# Windows API constants for click-through
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


class PetWindow(QWidget):
    """
    Main transparent desktop pet window for '大肥鱼' (Whale Musume).
    Supports high-res character animation, drag/drop rebound physics,
    click-through, scaling, multi-monitor geometry, and tray controls.
    """

    def __init__(self, backend_url="http://127.0.0.1:8000"):
        super().__init__()
        self.backend_url = backend_url
        self.drag_position = QPoint()
        self.drag_start_time = 0.0
        self.is_dragging = False
        self.is_click_through = False

        # Frameless, transparent, always on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

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

        # State and sync
        self.current_mood = "探索兴起"
        self.current_bubble_text = "今天有什么新奇事物在等着我们呢？咕噜噜~"

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
            # Double click tray: restore from click-through and show
            if self.is_click_through:
                self.toggle_click_through(False)
            self.show()
            self.raise_()
            self.activateWindow()

    def set_pet_scale(self, scale: float):
        self.current_scale = scale
        self.renderer.set_scale(scale)
        self.adjustSize()
        # Reposition bubble if visible
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
        def _fetch():
            try:
                res = httpx.get(f"{self.backend_url}/api/pet/status", timeout=2.5)
                if res.status_code == 200:
                    data = res.json()
                    new_state = data.get("state", "idle")
                    new_mood = data.get("mood", "探索兴起")
                    new_bubble = data.get("bubble_text", "")

                    self.current_mood = new_mood
                    if new_bubble:
                        self.current_bubble_text = new_bubble
                    self.renderer.set_state(new_state)
            except Exception:
                pass  # Graceful silent pass if backend is offline

        threading.Thread(target=_fetch, daemon=True).start()

    def _update_bubble_position(self):
        pos = self.mapToGlobal(QPoint(0, 0))
        # Center horizontally above pet
        bx = pos.x() + (self.width() - self.bubble.width()) // 2
        by = pos.y() - self.bubble.height() - 10
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
        self.renderer.set_state("thinking")
        self.bubble.show_message("正在探索", "大肥鱼正游出水缸，去B站看看有什么新奇的科学与创意视频...", duration_ms=4000)

        def _do_explore():
            try:
                res = httpx.post(f"{self.backend_url}/api/discovery/explore", timeout=15.0)
                if res.status_code == 200:
                    candidates = res.json()
                    if candidates:
                        first = candidates[0]
                        self.renderer.set_state("happy")
                        self.current_mood = "大开眼界"
                        self.current_bubble_text = f"发现新视频：《{first.get('title')[:15]}...》！{first.get('reason')}"
                        QTimer.singleShot(0, self._show_bubble)
            except Exception:
                self.renderer.set_state("confused")

        threading.Thread(target=_do_explore, daemon=True).start()

    # --- Mouse Events for Dragging, Rebound and Interactions ---

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.is_click_through:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.drag_start_time = time.time()
            self.is_dragging = True
            self.renderer.set_state("drag")
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.is_dragging:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            if self.bubble.isVisible():
                self._update_bubble_position()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            duration = time.time() - self.drag_start_time

            # If it's a short click without significant drag (< 250ms), treat as touch interaction
            if duration < 0.25:
                click_pos = event.position()
                region = self.renderer.hit_test_region(click_pos.x(), click_pos.y())

                if region == "head":
                    self.renderer.set_state("headpat", temp_duration_ms=3500)
                    self.bubble.show_message("心动摸头", "摸摸头~ 咕噜噜！小肥鱼的呆毛蹭了蹭你的手心，充满电啦！✨", duration_ms=4000)
                elif region == "belly":
                    self.renderer.set_state("touch_belly", temp_duration_ms=3000)
                    self.bubble.show_message("好痒痒~", "噗嗤！别挠肚皮啦，小鲸鱼要笑翻到桌子底下去啦！(>▽<)", duration_ms=3500)
                elif region == "tail":
                    self.renderer.set_state("touch_tail", temp_duration_ms=3000)
                    self.bubble.show_message("羞羞护尾", "哇呀！尾巴是敏感区，不能随便揪的啦~ 摇两下抗议！(脸红)", duration_ms=3500)
                else:
                    self._show_bubble()
            else:
                # Released from drag: execute gravity fall & multi-bounce landing rebound
                self.renderer.trigger_drop_rebound()
                # Ensure the window does not fall past the available desktop bottom
                screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
                avail_bottom = screen.availableGeometry().bottom()
                if self.geometry().bottom() > avail_bottom:
                    self.move(self.x(), avail_bottom - self.height())

            event.accept()

    def contextMenuEvent(self, event):
        if self.is_click_through:
            return
        menu = QMenu(self)
        self._build_context_menu(menu)
        menu.exec(QCursor.pos())

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
            ("🏃 向右走动 (Walk Right)", "walking_right"),
            ("🏃 向左走动 (Walk Left)", "walking_left"),
            ("🦘 活力跳跃 (Jump)", "jumping"),
            ("💭 吐泡思考 (Thinking)", "thinking"),
            ("❓ 歪头疑惑 (Confused)", "confused"),
            ("🌟 欢呼开心 (Happy)", "happy"),
            ("😭 扁嘴委屈 (Aggrieved)", "aggrieved"),
            ("😎 得意叉腰 (Proud)", "proud"),
            ("📖 专注读书 (Reading)", "reading"),
            ("💻 编写代码 (Computer)", "computer"),
            ("📺 观察视频 (Watching)", "watching"),
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
