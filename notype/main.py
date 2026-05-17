#!/usr/bin/env python3
"""
notype - macOS 語音輸入工具
按住快捷鍵說話，放開後 Groq Whisper 辨識 + LLM 潤稿 → 自動貼到游標位置
"""

import logging
import subprocess
import sys
import threading

from config.settings import Settings
from core.recorder import AudioRecorder
from core.stt import SpeechToText
from core.llm import LLMProcessor
from core.injector import TextInjector
from core.hotkey import HotkeyManager
from core.sounds import play_start, play_stop, play_error

# 簡轉繁
try:
    from opencc import OpenCC
    _cc = OpenCC("s2twp")
except Exception:
    _cc = None

MIN_RECORDING_SECONDS = 0.3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("notype")


def notify(title: str, msg: str = ""):
    """macOS 系統通知"""
    safe_msg = msg.replace('"', "'")
    safe_title = title.replace('"', "'")
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{safe_msg}" with title "{safe_title}"'],
            capture_output=True, timeout=2,
        )
    except Exception:
        pass


class Notype:
    """主應用程式"""

    def __init__(self):
        self.settings = Settings()
        self.settings.load()

        # 檢查 API Key
        cfg = self.settings.get_config()
        stt_provider = cfg.get("sttProvider", "groq")
        if not self.settings.get_api_key(stt_provider):
            raise SystemExit(
                f"\n❌ {stt_provider} API Key 未設定\n"
                f"請編輯：{self.settings.config_path}\n"
                f"或設定環境變數 GROQ_API_KEY"
            )

        self.recorder = AudioRecorder()
        self.stt = SpeechToText(self.settings)
        self.llm = LLMProcessor(self.settings)
        self.injector = TextInjector(self.settings)
        self.hotkey = HotkeyManager(self.settings)

        self._state_lock = threading.RLock()
        self.is_recording = False
        self.processing = False

    def on_press(self):
        with self._state_lock:
            if self.is_recording or self.processing:
                return
            self.is_recording = True

        cfg = self.settings.get_config()
        if cfg.get("playSounds", True):
            play_start()

        self.recorder.start()
        logger.info("🔴 錄音中")

    def on_release(self):
        with self._state_lock:
            if not self.is_recording:
                return
            self.is_recording = False
            self.processing = True

        cfg = self.settings.get_config()
        if cfg.get("playSounds", True):
            play_stop()

        # 背景處理：辨識 + 潤稿 + 注入
        threading.Thread(target=self._process, daemon=True).start()

    def _process(self):
        try:
            audio = self.recorder.stop()
            if audio is None or len(audio) < int(MIN_RECORDING_SECONDS * 16000):
                logger.info("（錄音太短）")
                return

            # STT
            logger.info("⏳ 辨識中…")
            raw_text = self.stt.transcribe(audio)
            if not raw_text:
                logger.info("（未偵測到語音）")
                return
            logger.info("📝 原文：%s", raw_text)

            # 簡 → 繁
            cfg = self.settings.get_config()
            if cfg.get("convertToTraditional", True) and _cc:
                raw_text = _cc.convert(raw_text)

            # LLM 潤稿
            if cfg.get("polish", True):
                text = self.llm.polish(raw_text)
                logger.info("✨ 潤稿：%s", text)
            else:
                text = raw_text

            # 注入
            if text:
                self.injector.inject(text)
                notify("notype ✓", text[:80])
                logger.info("✓ 完成")
        except Exception as e:
            logger.exception("處理失敗")
            notify("notype 錯誤", str(e)[:80])
            play_error()
        finally:
            with self._state_lock:
                self.processing = False

    def run(self):
        cfg = self.settings.get_config()
        hotkey_name = cfg.get("hotkey", "RightCmd")
        logger.info("notype 啟動完成")
        logger.info("快捷鍵：按住 %s 錄音，放開辨識（Ctrl+C 離開）", hotkey_name)
        logger.info("設定檔：%s", self.settings.config_path)
        notify("notype 就緒", f"按住 {hotkey_name} 錄音")

        self.hotkey.register(self.on_press, self.on_release)
        self.hotkey.start()
        try:
            self.hotkey.join()
        except KeyboardInterrupt:
            logger.info("離開")
            self.hotkey.stop()


if __name__ == "__main__":
    sys.exit(Notype().run() or 0)
