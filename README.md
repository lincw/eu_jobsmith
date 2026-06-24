# 台灣 AI 求職 Co-pilot

用一個 multi-agent 系統，幫你找 AI agent 的工作。M1：貼 JD → 解析 → 匹配評分。

## 設定
1. `python -m venv .venv && .venv\Scripts\activate`（Windows）
2. `pip install -r requirements.txt`
3. 複製 `.env.example` 為 `.env`，填入 `ANTHROPIC_API_KEY`

## 執行
`python -m app.cli data/demo_jobs/ai_engineer.txt`

## 測試
`pytest`（預設略過 live API 測試；跑真打 API 的測試：`pytest -m live`）

## LLM 後端（可切換）
於 `.env` 設 `LLM_BACKEND`：
- `anthropic`（預設）：需 `ANTHROPIC_API_KEY`
- `qianfan`（百度千帆 Coding Plan，OpenAI 相容）：需 `QIANFAN_API_KEY`；模型分層用 `deepseek-v3.2`／`minimax-m2.5`／`deepseek-v4-pro`

## Web UI（看得見的編排）
從專案根目錄啟動：
```
.venv\Scripts\python.exe -m uvicorn app.server:app --port 8000
```
開瀏覽器到 http://localhost:8000 → 「載入範例」→「開始」→ 看左欄 agent 即時編排、右欄成品分頁 → 出現「核可／不核可」→ 按下後流程完成。

（要真的跑出內容需先在 `.env` 設好後端與金鑰，例如 `LLM_BACKEND=qianfan` + `QIANFAN_API_KEY=...`。）

## 桌面 App（原生視窗，不用開瀏覽器）
本機跑、用你自己的 Claude Code / Codex CLI 訂閱（免 API key）。雙擊即開一個原生視窗：

1. 建置前端（產生 `frontend/dist`，桌面視窗會載入它）：
   ```
   cd frontend && npm install && npm run build
   ```
2. 安裝桌面相依（含 `pywebview`）：`.venv\Scripts\python.exe -m pip install -r requirements.txt`
3. 雙擊 `desktop.bat`（或 `.venv\Scripts\python.exe desktop.py`）。

備註：Windows 需有 WebView2 執行階段（Win11 內建）。若 8000 埠被佔用會自動改用空閒埠。
這仍是本機執行——遠端網站無法使用你本機的 CLI 訂閱；要做雲端版本需改用 API key 後端。
