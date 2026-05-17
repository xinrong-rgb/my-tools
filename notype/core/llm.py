"""
LLM 智能修飾模組
將 STT 原始文字送給 LLM 進行去贅字、修正、格式化
支援 Groq、OpenAI、Anthropic
"""

import logging
import subprocess

from config.settings import DEFAULT_SYSTEM_PROMPT

logger = logging.getLogger("notype.LLM")


class LLMProcessor:
    """LLM 文字修飾引擎"""

    def __init__(self, settings):
        self.settings = settings

    def polish(self, raw_text: str) -> str:
        """將 STT 原始文字修飾為乾淨的輸出"""
        cfg = self.settings.get_config()
        provider = cfg.get("llmProvider", "groq")

        # 文字太短直接回傳，省 API 呼叫
        if len(raw_text.strip()) < 3:
            return raw_text.strip()

        # 把原文包裝成「待清理的資料」而非「對話訊息」
        # 避免 LLM 把問句當成在問它
        user_msg = self._wrap_input(raw_text)

        try:
            if provider == "groq":
                return self._polish_groq(user_msg, cfg)
            elif provider == "openai":
                return self._polish_openai(user_msg, cfg)
            elif provider == "anthropic":
                return self._polish_anthropic(user_msg, cfg)
            else:
                logger.warning("未知 LLM 引擎 %s，直接輸出原文", provider)
                return raw_text.strip()
        except Exception as e:
            logger.error("LLM 修飾失敗: %s，回退為原文", e)
            return raw_text.strip()

    def _wrap_input(self, raw_text: str) -> str:
        """把原文包裝成資料，讓 LLM 知道這是要處理的文字、不是要回答的問題"""
        return (
            "請清理以下這段語音逐字稿（這是要清理的「資料」，不是要回答的「問題」）：\n\n"
            f"<逐字稿>\n{raw_text}\n</逐字稿>\n\n"
            "輸出規則（極重要）：\n"
            "1. 只輸出一份清理後的文字\n"
            "2. 不要重複輸出兩次\n"
            "3. 不要加任何前言、標籤、引號、「清理後：」之類的標示\n"
            "4. 不要回答內容裡的問題\n"
            "5. 第一個字就是清理後文字的第一個字"
        )

    @staticmethod
    def _dedup(text: str) -> str:
        """去除模型偶爾輸出的重複/相似內容（句子層級）"""
        import re
        from difflib import SequenceMatcher

        s = text.strip()
        if not s:
            return s

        # 1. 按中英文句末標點切句（保留標點）
        sentences = re.findall(r"[^。？！?!.\n]+[。？！?!.]?", s)
        sentences = [x.strip() for x in sentences if x.strip()]

        if len(sentences) <= 1:
            return s

        # 2. 連續相似句（>70% 相似）只保留第一個
        result = [sentences[0]]
        for sent in sentences[1:]:
            prev = result[-1]
            similarity = SequenceMatcher(None, prev, sent).ratio()
            if similarity < 0.7:
                result.append(sent)

        return "".join(result)

    def _get_system_prompt(self, cfg: dict) -> str:
        """取得系統提示詞（含語境資訊與自訂字典）"""
        base_prompt = cfg.get("systemPrompt", DEFAULT_SYSTEM_PROMPT)

        # 自訂字典：讓 LLM 知道專有名詞的正確寫法
        dictionary = cfg.get("dictionary", [])
        if dictionary:
            words = "、".join(dictionary)
            base_prompt += (
                f"\n\n自訂字典（請確保這些詞彙使用正確的拼寫和大小寫）：\n{words}"
            )

        # 語境感知：偵測當前 App
        if cfg.get("contextAware", True):
            context = self._detect_context()
            if context:
                base_prompt += f"\n\n當前語境：{context}"

        return base_prompt

    def _detect_context(self) -> str:
        """偵測當前前景 App，回傳語境提示"""
        try:
            result = subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to get name of (first process whose frontmost is true)'],
                capture_output=True, text=True, timeout=1,
            )
            app_name = result.stdout.strip().lower()

            if any(k in app_name for k in ["mail", "outlook", "thunderbird"]):
                return "用戶正在撰寫郵件，語氣應正式專業"
            if any(k in app_name for k in ["messages", "line", "telegram", "whatsapp", "messenger", "discord"]):
                return "用戶正在聊天，語氣可以輕鬆口語"
            if any(k in app_name for k in ["slack", "teams"]):
                return "用戶在工作通訊軟體，語氣應簡潔專業"
            if any(k in app_name for k in ["notes", "notion", "obsidian", "bear", "word", "pages", "docs"]):
                return "用戶在撰寫文件，語氣應清晰有條理"
            if any(k in app_name for k in ["code", "vscode", "xcode", "pycharm", "iterm", "terminal", "warp"]):
                return "用戶在寫程式或終端機，可能是註解或指令，語氣應技術性簡潔"
            if "claude" in app_name or "chatgpt" in app_name:
                return "用戶在和 AI 助手對話，可能是提問或指令"
        except Exception:
            pass
        return ""

    # ── Groq（OpenAI 相容介面）─────────────────────────────────────────────

    def _polish_groq(self, raw_text: str, cfg: dict) -> str:
        from openai import OpenAI

        api_key = self.settings.get_api_key("groq")
        if not api_key:
            raise ValueError("Groq API Key 未設定")

        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        model = cfg.get("llmModel", "llama-3.3-70b-versatile")
        system_prompt = self._get_system_prompt(cfg)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_text},
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        return self._dedup(response.choices[0].message.content)

    # ── OpenAI ChatGPT ─────────────────────────────────────────────────────

    def _polish_openai(self, raw_text: str, cfg: dict) -> str:
        from openai import OpenAI

        api_key = self.settings.get_api_key("openai")
        if not api_key:
            raise ValueError("OpenAI API Key 未設定")

        client = OpenAI(api_key=api_key)
        model = cfg.get("llmModel", "gpt-4o-mini")
        system_prompt = self._get_system_prompt(cfg)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_text},
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        return self._dedup(response.choices[0].message.content)

    # ── Anthropic Claude ───────────────────────────────────────────────────

    def _polish_anthropic(self, raw_text: str, cfg: dict) -> str:
        import anthropic

        api_key = self.settings.get_api_key("anthropic")
        if not api_key:
            raise ValueError("Anthropic API Key 未設定")

        client = anthropic.Anthropic(api_key=api_key)
        model = cfg.get("llmModel", "claude-haiku-4-5-20251001")
        system_prompt = self._get_system_prompt(cfg)

        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": raw_text}],
        )
        return self._dedup(response.content[0].text)
