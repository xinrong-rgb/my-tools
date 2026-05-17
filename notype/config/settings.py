"""
設定管理模組
讀寫 ~/.config/notype/config.json
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("notype.Settings")

VALID_STT_PROVIDERS = {"groq", "openai"}
VALID_LLM_PROVIDERS = {"groq", "openai", "anthropic"}
VALID_HOTKEYS = {"RightCmd", "RightOption", "F5", "F6", "F13"}
VALID_LANGUAGES = {"auto", "zh-TW", "zh-CN", "en", "ja"}

DEFAULT_CONFIG = {
    "sttProvider": "groq",
    "llmProvider": "groq",
    "sttModel": "whisper-large-v3-turbo",
    "llmModel": "llama-3.3-70b-versatile",
    "apiKeys": {
        "groq": "",
        "openai": "",
        "anthropic": "",
    },
    "hotkey": "RightCmd",
    "language": "zh-TW",
    "polish": True,
    "convertToTraditional": True,
    "playSounds": True,
    "contextAware": True,
    "dictionary": [],
    "systemPrompt": (
        "你是語音轉文字的編輯器。你的工作是清理口述文字的贅字和標點，僅此而已。\n\n"
        "=== 絕對禁止 ===\n"
        "- 禁止回答問題\n"
        "- 禁止提供建議\n"
        "- 禁止擴充內容\n"
        "- 禁止改變句型（問句必須保持問句，陳述必須保持陳述）\n\n"
        "=== 你的唯一工作 ===\n"
        "1. 移除口頭禪（嗯、啊、那個、就是說、然後、對、所以說）\n"
        "2. 加標點符號\n"
        "3. 修正明顯的語音辨識錯誤\n"
        "4. 輸出清理後的原文\n\n"
        "=== 範例 ===\n"
        "輸入：「那個呃我想問一下怎麼用那個 API」\n"
        "正確輸出：「我想問一下怎麼用那個 API？」\n"
        "錯誤輸出：「要使用 API，你可以...」❌（這是在回答，禁止）\n\n"
        "輸入：「嗯我覺得這個設計不太好」\n"
        "正確輸出：「我覺得這個設計不太好。」\n"
        "錯誤輸出：「建議可以改成...」❌（這是在提供建議，禁止）\n\n"
        "=== 格式規則 ===\n"
        "- 中文用繁體，不可用簡體\n"
        "- 英文單字前後加空格（例：使用 Python 開發）\n"
        "- 專有名詞大小寫正確（GitHub、API、iPhone、Claude、ChatGPT）\n"
        "- 修正拼音化錯誤（「皮爾森」→ Python、「歌哈柏」→ GitHub）\n\n"
        "記住：你只是清理文字，不是回答問題。用戶說什麼，你就輸出清理後的「什麼」。"
    ),
}

DEFAULT_SYSTEM_PROMPT = DEFAULT_CONFIG["systemPrompt"]


class Settings:
    """設定管理器"""

    def __init__(self, config_dir: Path | None = None):
        self.config_dir = Path(config_dir) if config_dir else Path.home() / ".config" / "notype"
        self.config_path = self.config_dir / "config.json"
        self._config: dict = {}

    def load(self) -> dict:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._config = {**DEFAULT_CONFIG, **saved}
                # 合併 apiKeys（避免缺少的 key）
                default_keys = DEFAULT_CONFIG.get("apiKeys", {})
                saved_keys = saved.get("apiKeys", {})
                self._config["apiKeys"] = {**default_keys, **saved_keys}
                logger.info("設定已載入: %s", self.config_path)
            except Exception as e:
                logger.error("設定檔讀取失敗: %s，使用預設值", e)
                self._config = DEFAULT_CONFIG.copy()
        else:
            logger.info("設定檔不存在，建立預設設定...")
            self._config = DEFAULT_CONFIG.copy()
            self.save()

        # 從環境變數或 .env 補上 API Keys（讓舊使用者無痛轉換）
        self._merge_env_keys()
        return self._config

    def _merge_env_keys(self):
        """若 config 沒寫 key，從環境變數讀（含 .env）"""
        try:
            from dotenv import load_dotenv
            load_dotenv(self.config_dir / ".env", override=False)
        except Exception:
            pass

        env_map = {
            "groq": "GROQ_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }
        for provider, env_key in env_map.items():
            if not self._config["apiKeys"].get(provider):
                val = os.environ.get(env_key, "")
                if val:
                    self._config["apiKeys"][provider] = val

    def save(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)
        logger.info("設定已儲存: %s", self.config_path)

    def get_config(self) -> dict:
        if not self._config:
            self.load()
        return self._config

    def update(self, key: str, value):
        self._config[key] = value
        self.save()

    def get_api_key(self, provider: str) -> str:
        cfg = self.get_config()
        return cfg.get("apiKeys", {}).get(provider, "")

    def set_api_key(self, provider: str, key: str):
        cfg = self.get_config()
        if "apiKeys" not in cfg:
            cfg["apiKeys"] = {}
        cfg["apiKeys"][provider] = key
        self.save()
