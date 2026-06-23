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
