"""
全域快捷鍵管理（macOS / pynput）
Push-to-Talk：按下觸發開始、放開觸發停止
預設使用右 ⌘ (Right Command)，避免和系統快捷鍵衝突
"""

import logging
from pynput import keyboard

logger = logging.getLogger("notype.Hotkey")

# 設定字串 → pynput key
KEY_MAP = {
    "RightCmd": keyboard.Key.cmd_r,
    "RightOption": keyboard.Key.alt_r,
    "F5": keyboard.Key.f5,
    "F6": keyboard.Key.f6,
    "F13": keyboard.Key.f13,
}


class HotkeyManager:
    """快捷鍵監聽器"""

    def __init__(self, settings):
        self.settings = settings
        self._listener: keyboard.Listener | None = None
        self._on_press_cb = None
        self._on_release_cb = None
        self._trigger_key = None

    def register(self, on_press, on_release):
        """註冊 push-to-talk 回呼"""
        self._on_press_cb = on_press
        self._on_release_cb = on_release
        self._refresh_key()

    def _refresh_key(self):
        cfg = self.settings.get_config()
        hotkey_name = cfg.get("hotkey", "RightCmd")
        self._trigger_key = KEY_MAP.get(hotkey_name, keyboard.Key.cmd_r)
        logger.info("快捷鍵：%s", hotkey_name)

    def start(self):
        if self._listener:
            return
        self._listener = keyboard.Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
        )
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None

    def join(self):
        if self._listener:
            self._listener.join()

    def _handle_press(self, key):
        if key == self._trigger_key and self._on_press_cb:
            self._on_press_cb()

    def _handle_release(self, key):
        if key == self._trigger_key and self._on_release_cb:
            self._on_release_cb()
