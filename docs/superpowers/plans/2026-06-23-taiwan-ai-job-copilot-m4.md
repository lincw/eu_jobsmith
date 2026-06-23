# 台灣 AI 求職 Co-pilot — M4 實作計畫（可插拔 LLM 後端 + 看得見的編排 Web UI）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (1) 把 LLM 後端做成可插拔（Anthropic API／百度千帆 OpenAI 相容，環境變數切換）並內建重試；(2) 用 FastAPI 以 SSE 串流跑反思迴圈圖、用 HTTP 處理 human-in-the-loop 的 interrupt/resume；(3) 一個 FastAPI 直接服務的單頁前端，呈現「看得見的編排」（左：agent 即時追蹤；右：成品分頁）。

**Architecture:** 既有 LangGraph 圖完全不動——只把 `app/llm.py get_llm()` 換成多後端（agents 用 `.with_structured_output()` 的程式碼一行都不改，因為 `ChatAnthropic` 與 `ChatOpenAI` 介面相同）。新增 `app/server.py`（FastAPI）持有「單一」圖實例（共用同一個 MemorySaver，讓 /resume 找得到 thread）。前端先用「FastAPI 服務的單一 HTML + 原生 JS（fetch 串流讀 SSE）」把串流與 interrupt 打通；Next.js + shadcn 升級列為 M5。

**Tech Stack:** 既有 + 新增 `langchain-openai`、`fastapi`、`uvicorn[standard]`、`httpx`（測試用）。前端用 Tailwind CDN + 原生 JS（無 node 工具鏈）。

## Global Constraints

- Python 3.11+。繁中為主。Pydantic v2 結構化輸出。
- **可插拔後端**：`LLM_BACKEND` ∈ {`anthropic`(預設), `qianfan`}。agents 程式碼不得因後端而改（只改 `get_llm`）。
- **百度千帆**：OpenAI 相容端點 `https://qianfan.baidubce.com/v2/coding`，Bearer = `QIANFAN_API_KEY`。實測可用模型分層：`cheap=minimax-m2.5`、`standard=deepseek-v3.2`、`deep=deepseek-v4-pro`（ERNIE/qwen-coder 在此方案被擋）。function calling 已實測可用 → `.with_structured_output()` 可行。會偶發 429 → 用 SDK `max_retries` 重試。
- **金鑰**：`ANTHROPIC_API_KEY` / `QIANFAN_API_KEY` 一律由 `.env`／環境變數提供，絕不寫死或 commit。
- **單一圖實例**：FastAPI 模組層建一次 `GRAPH = build_graph()`，/run 與 /resume 共用（MemorySaver 是 per-process；本機單 worker 跑）。
- 測試以 monkeypatch 注入假 agent（沿用既有），不打 API；FastAPI 用 `TestClient`。
- 環境 Windows+PowerShell；用 `.venv\Scripts\python.exe`。TDD、DRY、YAGNI、頻繁 commit。
- **M4 不含**（列為未來）：Next.js/shadcn 升級、JD URL 抓取、PDF 匯出、多使用者登入、`claude -p` 後端（見附錄 A，選做）。

---

## File Structure（M4 變動）

```
app/
  settings.py          # [改] 加 LLM_BACKEND 選擇 + 千帆 tier 表 + base url
  llm.py               # [改] get_llm 多後端 + max_retries
  server.py            # [新] FastAPI：/api/run、/api/resume、/api/sample、/(靜態頁)
  web/
    index.html         # [新] 看得見的編排單頁（Tailwind CDN + 原生 JS）
requirements.txt       # [改] 加 langchain-openai / fastapi / uvicorn / httpx
.env.example           # [改] 加 LLM_BACKEND / QIANFAN_API_KEY
pyproject.toml         # [改] 加 ruff 設定（順手清風格債）
.gitattributes         # [新] * text=auto eol=lf（解決 CRLF 警告）
tests/
  test_llm_backend.py  # [新] 後端選擇 + tier 對應
  test_server.py       # [新] FastAPI run/resume SSE（TestClient）
```

---

### Task 1: 可插拔 LLM 後端 + 重試 + 開發打磨

**Files:**
- Modify: `app/settings.py`
- Modify: `app/llm.py`
- Modify: `requirements.txt`、`.env.example`、`pyproject.toml`
- Create: `.gitattributes`
- Test: `tests/test_llm_backend.py`

**Interfaces (Produces):**
- `app.settings.LLM_BACKEND: str`、`app.settings.QIANFAN_MODEL_TIERS: dict[str,str]`、`app.settings.QIANFAN_BASE_URL: str`、`app.settings.get_model(tier)`（沿用，回 anthropic 表）
- `app.llm.get_llm(tier, *, temperature=0, max_tokens=2000)`：依 `LLM_BACKEND` 回 `ChatAnthropic` 或 `ChatOpenAI`（千帆），皆含 `max_retries`

- [ ] **Step 1: 加依賴與設定檔**

`requirements.txt` append：
```
langchain-openai>=0.2
fastapi>=0.110
uvicorn[standard]>=0.29
httpx>=0.27
```
安裝：`.venv\Scripts\python.exe -m pip install langchain-openai fastapi "uvicorn[standard]" httpx`

`.env.example` append：
```
# LLM 後端：anthropic（預設）或 qianfan（百度千帆 OpenAI 相容）
LLM_BACKEND=anthropic
# 用 qianfan 時需要（Coding Plan 的 bce-v3/... token）
QIANFAN_API_KEY=bce-v3/xxxxx
```

`pyproject.toml` append（ruff 設定，順手清風格債如 E402）：
```toml
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I"]
# 測試檔的 append 式 mid-file import 容許
[tool.ruff.lint.per-file-ignores]
"tests/*" = ["E402"]
```

Create `.gitattributes`:
```
* text=auto eol=lf
```

- [ ] **Step 2: 寫後端選擇的失敗測試 — Create `tests/test_llm_backend.py`**

```python
import importlib

import app.settings as settings_mod
import app.llm as llm_mod


def _reload(monkeypatch, backend):
    monkeypatch.setenv("LLM_BACKEND", backend)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("QIANFAN_API_KEY", "bce-v3/test")
    importlib.reload(settings_mod)
    importlib.reload(llm_mod)
    return llm_mod


def test_anthropic_backend_selected(monkeypatch):
    m = _reload(monkeypatch, "anthropic")
    llm = m.get_llm("standard")
    assert llm.model == "claude-sonnet-4-6"


def test_qianfan_backend_selected(monkeypatch):
    m = _reload(monkeypatch, "qianfan")
    llm = m.get_llm("standard")
    # ChatOpenAI 的模型屬性名為 model_name
    assert getattr(llm, "model_name", getattr(llm, "model", "")) == "deepseek-v3.2"


def test_qianfan_tier_map(monkeypatch):
    m = _reload(monkeypatch, "qianfan")
    assert m.get_llm("cheap").model_name == "minimax-m2.5"
    assert m.get_llm("deep").model_name == "deepseek-v4-pro"


def test_unknown_backend_raises(monkeypatch):
    m = _reload(monkeypatch, "nonsense")
    import pytest
    with pytest.raises(ValueError):
        m.get_llm("standard")
```

> 註：測試用 `importlib.reload` 讓 `LLM_BACKEND` 在匯入時生效。實作時 `get_llm` 內部讀 `settings.LLM_BACKEND`（每次呼叫讀，較單純）亦可——若採後者，可把測試改成不 reload、直接 `monkeypatch.setattr(settings_mod, "LLM_BACKEND", ...)`。實作者擇一並讓測試一致。

- [ ] **Step 3: 執行確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_llm_backend.py -v`
Expected: FAIL（`QIANFAN_MODEL_TIERS` / 多後端尚未實作）

- [ ] **Step 4: 改 `app/settings.py`**（在現有內容後加，不動既有 `MODEL_TIERS`/`get_model`）

```python
import os

# LLM 後端選擇：anthropic（預設）或 qianfan
LLM_BACKEND: str = os.environ.get("LLM_BACKEND", "anthropic")

# 百度千帆（Coding Plan，OpenAI 相容）— 實測可用的模型分層
QIANFAN_BASE_URL = "https://qianfan.baidubce.com/v2/coding"
QIANFAN_MODEL_TIERS: dict[str, str] = {
    "cheap": "minimax-m2.5",
    "standard": "deepseek-v3.2",
    "deep": "deepseek-v4-pro",
}
```

- [ ] **Step 5: 改 `app/llm.py`（多後端 + 重試）**

```python
"""依 LLM_BACKEND 建立 LLM（介面一致：.with_structured_output(...).invoke(...)）。"""
import os

from app import settings
from app.settings import get_model


def get_llm(tier: str, *, temperature: float = 0, max_tokens: int = 2000):
    """依分層與後端回傳設定好的 chat model（含重試）。"""
    backend = settings.LLM_BACKEND
    if backend == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=get_model(tier),
            temperature=temperature,
            max_tokens=max_tokens,
            max_retries=4,
        )
    if backend == "qianfan":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            base_url=settings.QIANFAN_BASE_URL,
            api_key=os.environ.get("QIANFAN_API_KEY", "missing"),
            model=settings.QIANFAN_MODEL_TIERS[tier],
            temperature=temperature,
            max_tokens=max_tokens,
            max_retries=4,  # 應付偶發 429 coding_plan_cluster_rate_limited
        )
    raise ValueError(f"unknown LLM_BACKEND: {backend!r}")
```

> 註：若你選「每次呼叫讀 settings.LLM_BACKEND」而非 reload，需確保 `app/llm.py` 內是 `settings.LLM_BACKEND`（屬性存取）而非 `from app.settings import LLM_BACKEND`（值快照），測試才好 monkeypatch。

- [ ] **Step 6: 確認通過 + 全套**

Run: `.venv\Scripts\python.exe -m pytest tests/test_llm_backend.py -v` → PASS
Run: `.venv\Scripts\python.exe -m pytest` → 全綠（既有 agent 測試不受影響，因為它們 monkeypatch get_llm）

- [ ] **Step 7:（選用）跑 ruff 清風格債**

Run: `.venv\Scripts\python.exe -m pip install ruff; .venv\Scripts\python.exe -m ruff check . --fix`
（把先前累積的 E402/import 排序等清掉；確認 `pytest` 仍全綠）

- [ ] **Step 8: Commit**

```bash
git add app/settings.py app/llm.py tests/test_llm_backend.py requirements.txt .env.example pyproject.toml .gitattributes
git commit -m "feat(m4): pluggable LLM backend (anthropic/qianfan) with retries + ruff/gitattributes"
```

---

### Task 2: FastAPI 伺服器（SSE 串流 + interrupt/resume）

**Files:**
- Create: `app/server.py`
- Test: `tests/test_server.py`

**Interfaces (Produces):**
- `app.server.app`（FastAPI 實例）
- `app.server.GRAPH`（模組層單一圖；測試會 monkeypatch graph 模組的 agent）
- `app.server.serialize_update(update: dict) -> dict`（把含 Pydantic 的 state 更新轉成可 JSON）
- Endpoints：`POST /api/run`（body `{jd_text}` → SSE）、`POST /api/resume`（body `{thread_id, decision}` → SSE）、`GET /api/sample`（回 demo JD 文字）、`GET /`（回前端 HTML）

**SSE 事件格式（每行 `data: <json>\n\n`）：**
- `{"type":"start","thread_id": "..."}`
- `{"type":"node","node":"match","data":{...}}`（每個節點完成後）
- `{"type":"interrupt","thread_id":"...","payload":{...}}`（停在人工關卡）
- `{"type":"done"}`（流程結束）

- [ ] **Step 1: 失敗測試 — Create `tests/test_server.py`**

```python
import json

from fastapi.testclient import TestClient

from app.models import (
    ParsedJob, MatchReport, CompanyBrief, TailoredResume, CoverLetter,
    InterviewKit, CritiqueReport,
)
from app import graph as graph_mod
from app import server as server_mod


def _patch_agents(monkeypatch):
    monkeypatch.setattr(graph_mod, "parse_job",
                        lambda jd_text: ParsedJob(title="AI 工程師", company="未來智能"))
    monkeypatch.setattr(graph_mod, "match_profile",
                        lambda job, profile: MatchReport(score=82, recommend_proceed=True, reason="吻合"))
    monkeypatch.setattr(graph_mod, "research_company",
                        lambda name: CompanyBrief(company=name))
    monkeypatch.setattr(graph_mod, "tailor_resume",
                        lambda job, profile, feedback=None: TailoredResume(summary="履歷"))
    monkeypatch.setattr(graph_mod, "write_cover_letter",
                        lambda job, profile, company, feedback=None: CoverLetter(body="信"))
    monkeypatch.setattr(graph_mod, "prepare_interview",
                        lambda job, profile, company, feedback=None: InterviewKit())
    monkeypatch.setattr(graph_mod, "critique_package",
                        lambda job, r, c, k: CritiqueReport(resume_score=90, cover_letter_score=90,
                                                            interview_score=90, overall_pass=True))


def _parse_sse(text: str) -> list[dict]:
    events = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            events.append(json.loads(line[len("data:"):].strip()))
    return events


def test_sample_endpoint():
    client = TestClient(server_mod.app)
    r = client.get("/api/sample")
    assert r.status_code == 200
    assert "工程師" in r.json()["jd_text"]


def test_run_streams_to_interrupt_then_resume(monkeypatch):
    _patch_agents(monkeypatch)
    client = TestClient(server_mod.app)

    r = client.post("/api/run", json={"jd_text": "一些 JD"})
    assert r.status_code == 200
    events = _parse_sse(r.text)
    types = [e["type"] for e in events]
    assert types[0] == "start"
    assert "node" in types                      # 至少有節點事件
    assert types[-1] == "interrupt"             # 停在人工關卡
    thread_id = events[0]["thread_id"]

    r2 = client.post("/api/resume", json={"thread_id": thread_id, "decision": "y"})
    assert r2.status_code == 200
    ev2 = _parse_sse(r2.text)
    assert ev2[-1]["type"] == "done"
    # 結束後 approved 應為 True（從某個 node 事件帶出，或最後 done 帶 final）
    assert any(e.get("type") == "node" for e in ev2)


def test_run_stop_path_finishes_without_interrupt(monkeypatch):
    _patch_agents(monkeypatch)
    monkeypatch.setattr(graph_mod, "match_profile",
                        lambda job, profile: MatchReport(score=30, recommend_proceed=False, reason="不符"))
    client = TestClient(server_mod.app)
    r = client.post("/api/run", json={"jd_text": "一些 JD"})
    events = _parse_sse(r.text)
    types = [e["type"] for e in events]
    assert "interrupt" not in types
    assert types[-1] == "done"
```

- [ ] **Step 2: 執行確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_server.py -v`
Expected: FAIL（`No module named 'app.server'`）

- [ ] **Step 3: 實作 — Create `app/server.py`**

```python
"""FastAPI：以 SSE 串流跑反思迴圈圖，並用 HTTP 處理 human-in-the-loop。"""
import json
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from langgraph.types import Command

from app.cli import load_profile
from app.graph import build_graph

app = FastAPI(title="台灣 AI 求職 Co-pilot")

# 單一圖實例：/run 與 /resume 共用同一個 MemorySaver（per-process）。
GRAPH = build_graph()

_WEB_DIR = Path(__file__).parent / "web"


def serialize_update(update: dict) -> dict:
    """把 LangGraph 的 state 更新（可能含 Pydantic）轉成可 JSON 的 dict。"""
    out = {}
    for k, v in update.items():
        if isinstance(v, BaseModel):
            out[k] = v.model_dump()
        else:
            out[k] = v
    return out


def _sse(obj: dict) -> str:
    return "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"


def _stream(graph_input, config):
    """跑 graph.stream(updates)，逐節點 yield SSE；結束時判斷是否停在 interrupt。"""
    for chunk in GRAPH.stream(graph_input, config, stream_mode="updates"):
        for node, update in chunk.items():
            if node == "__interrupt__":
                continue
            yield _sse({"type": "node", "node": node, "data": serialize_update(update or {})})
    snapshot = GRAPH.get_state(config)
    if snapshot.next:  # 還有待跑節點 → 停在 human_gate interrupt
        payload = {}
        if snapshot.tasks and snapshot.tasks[0].interrupts:
            payload = snapshot.tasks[0].interrupts[0].value
        yield _sse({"type": "interrupt",
                    "thread_id": config["configurable"]["thread_id"],
                    "payload": payload})
    else:
        yield _sse({"type": "done"})


class RunBody(BaseModel):
    jd_text: str
    profile_path: str = "data/demo_profile.json"


class ResumeBody(BaseModel):
    thread_id: str
    decision: str


@app.get("/api/sample")
def sample():
    jd = (Path("data/demo_jobs/ai_engineer.txt")).read_text(encoding="utf-8")
    return {"jd_text": jd}


@app.post("/api/run")
def run(body: RunBody):
    profile = load_profile(body.profile_path)
    thread_id = uuid.uuid4().hex
    config = {"configurable": {"thread_id": thread_id}}
    initial = {
        "jd_text": body.jd_text, "profile": profile,
        "parsed_job": None, "match_report": None, "company_brief": None,
        "tailored_resume": None, "cover_letter": None, "interview_kit": None,
        "critique": None, "revision_count": 0, "approved": None,
    }

    def gen():
        yield _sse({"type": "start", "thread_id": thread_id})
        yield from _stream(initial, config)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/resume")
def resume(body: ResumeBody):
    config = {"configurable": {"thread_id": body.thread_id}}

    def gen():
        yield _sse({"type": "start", "thread_id": body.thread_id})
        yield from _stream(Command(resume=body.decision), config)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/", response_class=HTMLResponse)
def index():
    return (_WEB_DIR / "index.html").read_text(encoding="utf-8")
```

- [ ] **Step 4: 先建一個最小 `app/web/index.html` 佔位（讓 `GET /` 不 500）**

Create `app/web/index.html`（內容暫時佔位，Task 3 會換成完整前端）：
```html
<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>placeholder</title><body>ok</body></html>
```

- [ ] **Step 5: 確認通過 + 全套**

Run: `.venv\Scripts\python.exe -m pytest tests/test_server.py -v` → PASS（3 passed）
Run: `.venv\Scripts\python.exe -m pytest` → 全綠

> 若 `snapshot.tasks[0].interrupts` 在你安裝的 LangGraph 版本結構不同（例如取值方式不一樣）而 interrupt 偵測失準，**停下回報 BLOCKED 與你印出的 `snapshot` 結構**；可改用「`snapshot.next` 非空即視為 interrupt、payload 給空 dict」這個較保守的判斷（前端仍可運作）。

- [ ] **Step 6: Commit**

```bash
git add app/server.py app/web/index.html tests/test_server.py
git commit -m "feat(m4): FastAPI server with SSE streaming + interrupt/resume endpoints"
```

---

### Task 3: 看得見的編排前端（單頁）

**Files:**
- Modify: `app/web/index.html`（換成完整前端）
- Test: `tests/test_server.py`（append 一個 `GET /` 回 HTML 的 smoke test）

**說明：** 前端是一個 HTML 檔，用 Tailwind CDN 美化、原生 JS 以 `fetch` 讀 SSE 串流（因為 `POST` 不能用 `EventSource`，改用 `fetch().body.getReader()` 解析 `data:` 行）。左欄即時亮起各 agent 節點，右欄分頁顯示成品；停在 interrupt 時出現「核可／不核可」。

- [ ] **Step 1: append smoke test 到 `tests/test_server.py`**

```python
def test_index_serves_html():
    client = TestClient(server_mod.app)
    r = client.get("/")
    assert r.status_code == 200
    assert "<html" in r.text.lower()
    assert "求職" in r.text  # 確認是我們的頁面而非佔位
```

- [ ] **Step 2: 執行確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_server.py::test_index_serves_html -v`
Expected: FAIL（佔位頁不含「求職」）

- [ ] **Step 3: 覆寫 `app/web/index.html` 為完整前端**

```html
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>台灣 AI 求職 Co-pilot</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-800">
  <div class="max-w-6xl mx-auto p-6">
    <h1 class="text-2xl font-bold mb-1">台灣 AI 求職 Co-pilot</h1>
    <p class="text-slate-500 mb-4">貼上職缺 JD → 看 agent 群即時工作 → 人工核可</p>

    <div class="flex gap-2 mb-4">
      <textarea id="jd" rows="4" class="flex-1 border rounded p-2 text-sm"
        placeholder="貼上職缺 JD 文字…"></textarea>
      <div class="flex flex-col gap-2">
        <button id="sample" class="px-3 py-2 bg-slate-200 rounded text-sm">載入範例</button>
        <button id="run" class="px-3 py-2 bg-indigo-600 text-white rounded text-sm">開始</button>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- 左：即時編排追蹤 -->
      <div class="border rounded bg-white p-4">
        <h2 class="font-semibold mb-2">即時編排追蹤</h2>
        <ul id="trace" class="space-y-1 text-sm font-mono"></ul>
        <div id="status" class="mt-3 text-xs text-slate-500"></div>
      </div>
      <!-- 右：成品 -->
      <div class="border rounded bg-white p-4">
        <div id="tabs" class="flex flex-wrap gap-1 mb-2 text-sm"></div>
        <pre id="panel" class="whitespace-pre-wrap text-sm bg-slate-50 p-3 rounded min-h-[200px]"></pre>
        <div id="approve" class="mt-3 hidden">
          <span class="text-sm mr-2">這份投遞包要核可嗎？</span>
          <button data-d="y" class="approve-btn px-3 py-1 bg-emerald-600 text-white rounded text-sm">核可</button>
          <button data-d="n" class="approve-btn px-3 py-1 bg-rose-600 text-white rounded text-sm">不核可</button>
        </div>
      </div>
    </div>
  </div>

<script>
const NODE_LABELS = {
  parse: "① 解析 JD", match: "② 匹配評分", company_research: "⑧ 公司情報 🔍",
  resume_tailor: "③ 履歷客製", cover_letter: "④ 求職信", interview_prep: "⑤ 面試準備",
  join: "彙整", critic: "⑥ 品管/反思", human_gate: "⑦ 人工核可",
};
const collected = {};      // node -> data
let currentThread = null;

function addTrace(node) {
  const ul = document.getElementById("trace");
  const li = document.createElement("li");
  li.textContent = "✓ " + (NODE_LABELS[node] || node);
  ul.appendChild(li);
}
function renderTabs() {
  const tabs = document.getElementById("tabs");
  tabs.innerHTML = "";
  Object.keys(collected).forEach(k => {
    const b = document.createElement("button");
    b.className = "px-2 py-1 rounded bg-slate-200";
    b.textContent = NODE_LABELS[k] || k;
    b.onclick = () => document.getElementById("panel").textContent =
      JSON.stringify(collected[k], null, 2);
    tabs.appendChild(b);
  });
}
function setStatus(s){ document.getElementById("status").textContent = s; }

async function readStream(resp, onEvent) {
  const reader = resp.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, idx); buf = buf.slice(idx + 2);
      const line = chunk.split("\n").find(l => l.startsWith("data:"));
      if (line) onEvent(JSON.parse(line.slice(5).trim()));
    }
  }
}
function handle(ev) {
  if (ev.type === "start") { currentThread = ev.thread_id; setStatus("執行中… thread " + ev.thread_id.slice(0,8)); }
  else if (ev.type === "node") {
    addTrace(ev.node);
    Object.entries(ev.data || {}).forEach(([k, v]) => { if (v != null) collected[ev.node] = v; });
    renderTabs();
  }
  else if (ev.type === "interrupt") {
    setStatus("已停在人工核可關卡");
    document.getElementById("approve").classList.remove("hidden");
  }
  else if (ev.type === "done") { setStatus("完成 ✅"); }
}

document.getElementById("sample").onclick = async () => {
  const r = await fetch("/api/sample"); const j = await r.json();
  document.getElementById("jd").value = j.jd_text;
};
document.getElementById("run").onclick = async () => {
  document.getElementById("trace").innerHTML = "";
  document.getElementById("approve").classList.add("hidden");
  for (const k in collected) delete collected[k];
  renderTabs();
  const jd = document.getElementById("jd").value;
  const resp = await fetch("/api/run", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jd_text: jd }),
  });
  await readStream(resp, handle);
};
document.querySelectorAll(".approve-btn").forEach(btn => {
  btn.onclick = async () => {
    document.getElementById("approve").classList.add("hidden");
    const resp = await fetch("/api/resume", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id: currentThread, decision: btn.dataset.d }),
    });
    await readStream(resp, handle);
  };
});
</script>
</body>
</html>
```

- [ ] **Step 4: 確認通過 + 全套**

Run: `.venv\Scripts\python.exe -m pytest tests/test_server.py -v` → PASS（4 passed）
Run: `.venv\Scripts\python.exe -m pytest` → 全綠

- [ ] **Step 5: 手動驗證（需 `.env` 設好後端與金鑰）**

```powershell
# 用百度免額外付費後端：在 .env 設 LLM_BACKEND=qianfan、QIANFAN_API_KEY=...
.venv\Scripts\python.exe -m uvicorn app.server:app --reload --port 8000
```
瀏覽器開 `http://localhost:8000` → 按「載入範例」→「開始」→ 看左欄 agent 逐一亮起、右欄分頁出現成品 → 出現「核可」按鈕 → 按核可 → 狀態變「完成」。

- [ ] **Step 6: Commit**

```bash
git add app/web/index.html tests/test_server.py
git commit -m "feat(m4): visible-orchestration single-page UI (SSE + interrupt approval)"
```

---

### Task 4: README 更新 + demo 截圖/錄影指引

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新 README**（加「Web UI」「LLM 後端切換」兩節）

在 `README.md` 加：
````markdown
## LLM 後端（可切換）
於 `.env` 設 `LLM_BACKEND`：
- `anthropic`（預設）：需 `ANTHROPIC_API_KEY`
- `qianfan`（百度千帆 Coding Plan，OpenAI 相容）：需 `QIANFAN_API_KEY`；分層用 deepseek-v3.2 / minimax-m2.5 / deepseek-v4-pro

## Web UI（看得見的編排）
`.venv\Scripts\python.exe -m uvicorn app.server:app --port 8000`
開 http://localhost:8000 → 載入範例 → 開始 → 看 agent 即時編排 → 人工核可。
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs(m4): document web UI and pluggable LLM backend"
```

---

## 附錄 A：（選做）`claude -p` 後端

若想用 Claude Code 訂閱（免 API key）當後端：在 `get_llm` 加第三個分支 `backend == "claude_cli"`，回傳一個自訂物件，其 `.with_structured_output(Model)` 回傳的物件之 `.invoke(messages)` 內部：
1. 把 messages 串成 prompt；
2. `subprocess.run(["claude","-p","--output-format","json","--json-schema", json.dumps(Model.model_json_schema()), prompt], ...)`；
3. 解析 stdout 的 JSON → `Model.model_validate(...)`。
注意：每次呼叫開子行程，整張圖一次 ~8–14 次呼叫會偏慢；且訂閱認證的程式化用途屬灰色地帶，僅建議本機個人使用。**因為百度後端已可用且更快，此項列為選做。**

---

## Self-Review（對照規格檢查）

**1. Spec coverage（M4 範圍 vs 設計規格 §7/§8/§9）：**
- 可插拔 LLM 後端（成本/provider 抽象）→ Task 1 ✓（Anthropic + 千帆；claude -p 附錄選做）
- 重試（千帆 429）→ Task 1 `max_retries` ✓
- FastAPI + SSE 串流 → Task 2 ✓
- human-in-the-loop 走 HTTP（interrupt → /api/resume）→ Task 2 ✓
- 看得見的編排 UI（左追蹤/右成品/核可）→ Task 3 ✓
- 開發打磨（ruff、.gitattributes）→ Task 1 ✓
- 文件 → Task 4 ✓
- （未來：Next.js/shadcn 升級、JD URL 抓取、PDF 匯出）→ 明確排除 ✓

**2. Placeholder scan：** Task 2 Step 4 的佔位 HTML 於 Task 3 Step 3 被正式前端取代（非殘留）；其餘無 TBD/TODO。✓

**3. Type/contract consistency：**
- agents 程式碼不因後端改變（`get_llm` 回的兩種 chat model 皆支援 `.with_structured_output().invoke()`）✓
- SSE 事件型別（start/node/interrupt/done）於 server 產生端與前端 `handle()` 消費端一致 ✓
- `/api/run`→`/api/resume` 以 `thread_id` 串接；server 用單一 `GRAPH`（共用 MemorySaver）✓
- 千帆模型分層字串（deepseek-v3.2 等）為實測可用值 ✓

**4. 風險旗標（已在文中標註 BLOCKED 指示）：** LangGraph `snapshot.tasks/interrupts` 結構若版本不同 → 回報並改用保守 interrupt 判斷。
