"""
語音轉文字模組 (Speech-to-Text)
支援 Groq Whisper、OpenAI Whisper
"""

import io
import logging
import numpy as np
from core.recorder import audio_to_wav_bytes

logger = logging.getLogger("notype.STT")

LANGUAGE_MAP = {"zh-TW": "zh", "zh-CN": "zh", "en": "en", "ja": "ja"}


class SpeechToText:
    """語音轉文字引擎"""

    def __init__(self, settings):
        self.settings = settings

    def transcribe(self, audio: np.ndarray) -> str:
        cfg = self.settings.get_config()
        provider = cfg.get("sttProvider", "groq")
        model = cfg.get("sttModel", "whisper-large-v3-turbo")
        language = cfg.get("language", "auto")
        dictionary = cfg.get("dictionary", [])

        # 組合自訂詞彙作為 Whisper prompt（Groq 限制 896 bytes）
        whisper_prompt = self._build_dict_prompt(dictionary)

        if provider == "groq":
            return self._transcribe_groq(audio, model, language, whisper_prompt)
        elif provider == "openai":
            return self._transcribe_openai(audio, model, language, whisper_prompt)
        else:
            raise ValueError(f"不支援的 STT 引擎: {provider}")

    def _build_dict_prompt(self, dictionary: list) -> str | None:
        """組合自訂詞彙為 Whisper prompt，控制在 890 bytes 內"""
        if not dictionary:
            return None
        parts = []
        current_bytes = 0
        for word in dictionary:
            word_bytes = len(word.encode("utf-8"))
            sep_bytes = 1 if parts else 0  # 逗號 1 byte
            if current_bytes + sep_bytes + word_bytes > 890:
                logger.warning("字典 prompt 截斷於 %d bytes", current_bytes)
                break
            parts.append(word)
            current_bytes += sep_bytes + word_bytes
        return ",".join(parts) if parts else None

    def _transcribe_groq(self, audio, model, language, prompt):
        from openai import OpenAI

        api_key = self.settings.get_api_key("groq")
        if not api_key:
            raise ValueError("Groq API Key 未設定")

        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

        wav_bytes = audio_to_wav_bytes(audio)
        audio_file = io.BytesIO(wav_bytes)
        audio_file.name = "recording.wav"

        kwargs = {"model": model, "file": audio_file, "response_format": "text"}
        if language and language != "auto":
            kwargs["language"] = LANGUAGE_MAP.get(language, language)
        if prompt:
            kwargs["prompt"] = prompt

        result = client.audio.transcriptions.create(**kwargs)
        return result.strip() if isinstance(result, str) else result.text.strip()

    def _transcribe_openai(self, audio, model, language, prompt):
        from openai import OpenAI

        api_key = self.settings.get_api_key("openai")
        if not api_key:
            raise ValueError("OpenAI API Key 未設定")

        client = OpenAI(api_key=api_key)

        wav_bytes = audio_to_wav_bytes(audio)
        audio_file = io.BytesIO(wav_bytes)
        audio_file.name = "recording.wav"

        kwargs = {"model": model, "file": audio_file, "response_format": "text"}
        if language and language != "auto":
            kwargs["language"] = LANGUAGE_MAP.get(language, language)
        if prompt:
            kwargs["prompt"] = prompt

        result = client.audio.transcriptions.create(**kwargs)
        return result.strip() if isinstance(result, str) else result.text.strip()
