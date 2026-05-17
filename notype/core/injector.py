"""
文字注入模組（macOS）
策略：寫入剪貼簿 → 模擬 ⌘V 貼上 → 還原原始剪貼簿
支援中文及任何 Unicode 字元
"""

import logging
import subprocess
import time

logger = logging.getLogger("notype.Injector")


class TextInjector:
    """文字注入器（剪貼簿 + Cmd+V）"""

    def __init__(self, settings=None):
        self.settings = settings

    def inject(self, text: str):
        if not text:
            return

        original = self._get_clipboard()
        self._set_clipboard(text)
        time.sleep(0.05)
        self._simulate_paste()
        time.sleep(0.3)
        # 還原原始剪貼簿
        self._set_clipboard(original or "")

    def _get_clipboard(self) -> str:
        try:
            return subprocess.run(
                ["pbpaste"], capture_output=True, text=True, timeout=2
            ).stdout
        except Exception as e:
            logger.debug("pbpaste 失敗: %s", e)
            return ""

    def _set_clipboard(self, text: str):
        try:
            subprocess.run(["pbcopy"], input=text, text=True, timeout=2)
        except Exception as e:
            logger.debug("pbcopy 失敗: %s", e)

    def _simulate_paste(self):
        script = 'tell application "System Events" to keystroke "v" using command down'
        try:
            subprocess.run(["osascript", "-e", script], timeout=3, capture_output=True)
        except Exception as e:
            logger.error("Cmd+V 模擬失敗: %s", e)
