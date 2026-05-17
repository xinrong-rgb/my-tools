"""
音訊錄製模組
使用 sounddevice 從預設麥克風錄音，回傳 numpy array
"""

import io
import logging
import threading
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as wav_write

logger = logging.getLogger("notype.Recorder")

SAMPLE_RATE = 16000  # Whisper 最佳取樣率


def audio_to_wav_bytes(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bytes:
    """numpy float32 audio → WAV bytes（給 STT API 上傳用）"""
    buf = io.BytesIO()
    int16 = (audio * 32767).clip(-32768, 32767).astype(np.int16)
    wav_write(buf, sample_rate, int16)
    return buf.getvalue()


class AudioRecorder:
    """麥克風錄音器"""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.recording = False
        self.frames: list = []
        self._thread = None

    def start(self):
        if self.recording:
            return
        self.recording = True
        self.frames = []
        self._thread = threading.Thread(target=self._record, daemon=True)
        self._thread.start()

    def _record(self):
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype="float32") as stream:
                while self.recording:
                    data, _ = stream.read(1024)
                    self.frames.append(data.copy())
        except Exception as e:
            logger.error("錄音失敗: %s", e)
            self.recording = False

    def stop(self) -> np.ndarray | None:
        """停止錄音，回傳 numpy float32 audio array（單聲道）"""
        if not self.recording:
            return None
        self.recording = False
        if self._thread:
            self._thread.join(timeout=2)
        if not self.frames:
            return None
        return np.concatenate(self.frames, axis=0).flatten()
