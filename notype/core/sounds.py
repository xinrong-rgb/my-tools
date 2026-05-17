"""
音效模組（macOS）
錄音開始/結束時播放系統音
使用 afplay 在背景執行緒播放，避免阻塞
"""

import logging
import subprocess
import threading
from pathlib import Path

logger = logging.getLogger("notype.Sounds")

# macOS 系統音檔（每台 Mac 都有）
SOUND_START = "/System/Library/Sounds/Tink.aiff"   # 清脆短音 → 開始
SOUND_STOP = "/System/Library/Sounds/Pop.aiff"     # 低沉短音 → 結束
SOUND_ERROR = "/System/Library/Sounds/Basso.aiff"  # 錯誤


def _play(path: str, volume: float = 0.5):
    """背景播放音檔"""
    if not Path(path).exists():
        return
    try:
        subprocess.run(
            ["afplay", "-v", str(volume), path],
            timeout=2, capture_output=True,
        )
    except Exception as e:
        logger.debug("afplay 失敗: %s", e)


def play_start():
    threading.Thread(target=_play, args=(SOUND_START,), daemon=True).start()


def play_stop():
    threading.Thread(target=_play, args=(SOUND_STOP,), daemon=True).start()


def play_error():
    threading.Thread(target=_play, args=(SOUND_ERROR,), daemon=True).start()
