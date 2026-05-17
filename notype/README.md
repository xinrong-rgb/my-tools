# notype

macOS push-to-talk 語音輸入工具。按住右 ⌘ → Groq Whisper 辨識 + LLM 潤稿 → 自動貼到游標。

## 架構
- `main.py` — 主程式
- `core/recorder.py` — 麥克風錄音 (sounddevice)
- `core/stt.py` — Groq/OpenAI Whisper
- `core/llm.py` — Groq/OpenAI/Anthropic LLM 潤稿（防回答問題、防重複輸出）
- `core/injector.py` — pbcopy + osascript Cmd+V
- `core/hotkey.py` — pynput 全域快捷鍵
- `core/sounds.py` — afplay 系統音效
- `config/settings.py` — JSON 設定管理

## 安裝
```bash
/opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

設定檔在 `~/.config/notype/config.json`，需填入 Groq API key（從 https://console.groq.com/keys 取得）。

## 啟動
```bash
source .venv/bin/activate && python main.py
```

或建立 `~/Applications/notype.app` 拖到 Dock 一鍵啟動。

## macOS 權限
首次執行會要求「輸入監控」權限（pynput 監聽鍵盤）。
