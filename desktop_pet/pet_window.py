from __future__ import annotations
import webbrowser
import threading
import httpx
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QAction, QCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QMenu, QApplication

from desktop_pet.fish_renderer import FishRenderer
from desktop_pet.speech_bubble import SpeechBubble
from desktop_pet.chat_dialog import ChatDialog


class PetWindow(QWidget):
    """
    Main transparent desktop pet window for '大肥鱼'.
    """

    def __init__(self, backend_url="http://127.0.0.1:8000"):
        super().__init__()
        self.backend_url = backend_url
        self.drag_position = QPoint()

        # Frameless, transparent, always on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Fish Vector Renderer
        self.renderer = FishRenderer(self)
        self.layout.addWidget(self.renderer)

        # Initial Position (bottom right of primary screen)
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 280, screen.height() - 280)

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
        self.current_bubble_text = "今天有什么新奇事物在等着我们呢？"

        # Polling timer for backend sync
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self._sync_backend_status)
        self.sync_timer.start(5000)

        # Initial bubble popup
        QTimer.singleShot(1200, self._show_bubble)

    def _sync_backend_status(self):
        def _fetch():
            try:
                res = httpx.get(f"{self.backend_url}/api/pet/status", timeout=2.0)
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

    def _show_bubble(self):
        # Position bubble above the fish
        pos = self.mapToGlobal(QPoint(0, 0))
        self.bubble.move(pos.x() - 10, pos.y() - self.bubble.height() - 10)
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

    # --- Mouse Events for Dragging and Interaction ---

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            # Follow bubble if visible
            if self.bubble.isVisible():
                pos = self.mapToGlobal(QPoint(0, 0))
                self.bubble.move(pos.x() - 10, pos.y() - self.bubble.height() - 10)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # If quick click without significant drag, toggle bubble
            self._show_bubble()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: white;
                border: 1px solid #cbd5e0;
                border-radius: 8px;
                padding: 6px;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #ebf8ff;
                color: #2b6cb0;
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

        menu.addSeparator()

        # State submenu
        state_menu = menu.addMenu("🎭 切换动画状态")
        states = [
            ("🌊 待机游动 (Idle)", "idle"),
            ("💭 吐泡思考 (Thinking)", "thinking"),
            ("🌟 欢呼跃起 (Happy)", "happy"),
            ("❓ 歪头疑惑 (Confused)", "confused"),
            ("📖 专注求知 (Studying)", "studying"),
            ("💤 沉睡休息 (Resting)", "resting"),
        ]
        for name, key in states:
            act = QAction(name, self)
            act.triggered.connect(lambda checked=False, k=key: self.renderer.set_state(k))
            state_menu.addAction(act)

        menu.addSeparator()

        # Action: Open Dashboard
        dashboard_act = QAction("🌐 打开管理面板", self)
        dashboard_act.triggered.connect(lambda: webbrowser.open("http://localhost:5173"))
        menu.addAction(dashboard_act)

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

        menu.exec(QCursor.pos())

    def _toggle_always_on_top(self):
        flags = self.windowFlags()
        if flags & Qt.WindowType.WindowStaysOnTopHint:
            self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        self.show()
