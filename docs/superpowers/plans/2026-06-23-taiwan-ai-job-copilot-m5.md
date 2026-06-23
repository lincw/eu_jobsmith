# M5：履歷上傳 + AI 健檢 + 產品級前端骨架 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development 執行本計畫。步驟用 `- [ ]` 追蹤。

**Goal:** 讓使用者上傳/貼履歷 → AI 結構化成 Profile 並做健檢評分（總分＋五項分數＋優缺點＋改寫建議），結果渲染在全新的 Vite+React+Tailwind 產品級前端，**不再出現 JSON**。

**Architecture:** 後端新增 `app/intake`（檔案攝取）、`app/agents/resume_eval`（結構化＋健檢，沿用既有 `get_llm`/`with_structured_output` 慣例）、新 SSE 端點 `POST /api/resume/evaluate`；前端在 `frontend/`（Vite React-TS + Tailwind），建置成靜態檔由 FastAPI 在 `/` 提供。既有投遞包流程與測試完全不動。

**Tech Stack:** Python 3.12 / FastAPI / Pydantic v2 / LangChain（structured output）；pypdf、python-docx、python-multipart；前端 Vite + React + TypeScript + Tailwind v3。

## Global Constraints

- 環境 Windows + PowerShell；Python 一律用 `.venv\Scripts\python.exe`。測試：`.venv\Scripts\python.exe -m pytest`（既有 55 passed / 1 deselected 必須維持綠）。
- Agent 一律透過 `from app.llm import get_llm`，用 `get_llm(tier).with_structured_output(Model).invoke([("system",...),("human",...)])`；分層：結構化用 `"cheap"`、健檢評分用 `"deep"`。
- 新模型放 `app/models.py`，繁體中文 `description`；所有面向使用者文字一律繁中。
- 測試用 `tests/conftest.py` 的 `FakeLLM` + `monkeypatch.setattr(模組, "get_llm", ...)`，禁止真打 LLM；真打外部的測試標 `@pytest.mark.live`。
- server 的 agent 函式以模組層 `from ... import 名稱` 匯入，使其可被 `monkeypatch.setattr(server_mod, "名稱", ...)`。
- ruff 設定（line-length 100、select E/F/I）；提交前可 `.venv\Scripts\python.exe -m ruff check .`。
- 不改 `app/graph.py`、`app/agents/*`（既有）、既有測試。
- YAGNI：M5 不做職缺探索、不做 PDF 匯出、不做 shadcn CLI（用 Tailwind 手刻乾淨元件即可達產品級；互動元件留待 M6/M7）。

---

### Task 1：新增履歷健檢資料模型

**Files:**
- Modify: `app/models.py`（在檔尾 append）
- Test: `tests/test_models.py`（append）

**Interfaces:**
- Produces: `ResumeIssue`、`ResumeRewrite`、`ResumeAssessment`（供 Task 3 agent、Task 4 server、Task 6 前端型別使用）

- [ ] **Step 1：寫失敗測試**（append 到 `tests/test_models.py`）

```python
from app.models import ResumeIssue, ResumeRewrite, ResumeAssessment


def test_resume_assessment_round_trips():
    a = ResumeAssessment(
        overall_score=78, clarity_score=80, impact_score=70,
        ats_keyword_score=75, localization_score=85, completeness_score=80,
        summary="整體不錯，量化成果可再加強。",
        strengths=["技術棧清楚"],
        issues=[ResumeIssue(severity="medium", area="工作經歷",
                            problem="缺乏量化", fix="加入數字，如『提升 30% 效能』")],
        rewrite_examples=[ResumeRewrite(original="負責後端開發",
                                        improved="主導後端 API 開發，支撐日活 5 萬",
                                        why="加入範圍與量化成果")],
    )
    dumped = a.model_dump()
    assert dumped["overall_score"] == 78
    assert dumped["issues"][0]["severity"] == "medium"
    assert dumped["rewrite_examples"][0]["improved"].startswith("主導")


def test_resume_assessment_score_bounds():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ResumeAssessment(
            overall_score=120, clarity_score=0, impact_score=0,
            ats_keyword_score=0, localization_score=0, completeness_score=0,
            summary="x",
        )
```

- [ ] **Step 2：跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_models.py -k resume_assessment -v`
Expected: FAIL（ImportError：尚無 ResumeAssessment）

- [ ] **Step 3：實作模型**（append 到 `app/models.py` 檔尾）

```python
class ResumeIssue(BaseModel):
    """履歷健檢發現的單一問題。"""
    severity: str = Field(description="嚴重度：high | medium | low")
    area: str = Field(description="問題所在區塊，如『工作經歷』『技能』")
    problem: str = Field(description="問題描述")
    fix: str = Field(description="具體可照做的修正建議")


class ResumeRewrite(BaseModel):
    """改寫前後對照範例。"""
    original: str = Field(description="原句")
    improved: str = Field(description="改寫後")
    why: str = Field(description="為何更好")


class ResumeAssessment(BaseModel):
    """② 履歷健檢報告。"""
    overall_score: int = Field(ge=0, le=100, description="整體分數")
    clarity_score: int = Field(ge=0, le=100, description="表達清晰度")
    impact_score: int = Field(ge=0, le=100, description="量化成果/影響力")
    ats_keyword_score: int = Field(ge=0, le=100, description="ATS 關鍵字涵蓋")
    localization_score: int = Field(ge=0, le=100, description="台灣履歷慣例符合度")
    completeness_score: int = Field(ge=0, le=100, description="完整度")
    summary: str = Field(description="一段總評")
    strengths: list[str] = Field(default_factory=list, description="優點清單")
    issues: list[ResumeIssue] = Field(default_factory=list, description="問題清單")
    rewrite_examples: list[ResumeRewrite] = Field(default_factory=list, description="改寫範例")
```

- [ ] **Step 4：跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_models.py -v`
Expected: PASS（全部）

- [ ] **Step 5：Commit**

```bash
git add app/models.py tests/test_models.py
git commit -m "feat(m5): add ResumeAssessment/ResumeIssue/ResumeRewrite models"
```

---

### Task 2：履歷檔案攝取（PDF/DOCX/文字 → 純文字）

**Files:**
- Create: `app/intake/__init__.py`（空檔）
- Create: `app/intake/resume_parser.py`
- Create: `tests/fixtures/sample_resume.pdf`（產生並提交的二進位 fixture）
- Modify: `requirements.txt`
- Test: `tests/test_resume_parser.py`

**Interfaces:**
- Produces: `extract_text(data: bytes, filename: str) -> str`（供 Task 4 server 使用）

- [ ] **Step 1：加相依套件**（append 到 `requirements.txt`）

```
pypdf>=4.0
python-docx>=1.1
python-multipart>=0.0.9
```

Run: `.venv\Scripts\python.exe -m pip install "pypdf>=4.0" "python-docx>=1.1" "python-multipart>=0.0.9"`

- [ ] **Step 2：產生 PDF fixture**（fpdf2 僅用於產生 fixture，不加入 requirements）

```bash
.venv\Scripts\python.exe -m pip install fpdf2
mkdir tests\fixtures 2>NUL
.venv\Scripts\python.exe -c "from fpdf import FPDF; p=FPDF(); p.add_page(); p.set_font('Helvetica', size=14); p.multi_cell(0, 8, 'Sample Resume\nName: Wang\nSkills: Python, LangChain'); p.output('tests/fixtures/sample_resume.pdf')"
```

確認檔案產生：`tests/fixtures/sample_resume.pdf` 存在且 > 0 bytes。

- [ ] **Step 3：寫失敗測試**（`tests/test_resume_parser.py`）

```python
from io import BytesIO
from pathlib import Path

from app.intake import resume_parser as rp


def test_extract_text_plaintext():
    data = "王小明\nPython 後端工程師".encode("utf-8")
    assert "Python" in rp.extract_text(data, "resume.txt")


def test_extract_text_unknown_ext_treated_as_text():
    data = "純文字履歷".encode("utf-8")
    assert rp.extract_text(data, "resume.unknown") == "純文字履歷"


def test_extract_text_docx():
    from docx import Document
    doc = Document()
    doc.add_paragraph("王小明")
    doc.add_paragraph("Python 後端工程師，3 年經驗")
    buf = BytesIO()
    doc.save(buf)
    text = rp.extract_text(buf.getvalue(), "resume.docx")
    assert "王小明" in text
    assert "後端工程師" in text


def test_extract_text_pdf():
    data = Path("tests/fixtures/sample_resume.pdf").read_bytes()
    text = rp.extract_text(data, "resume.pdf")
    assert "Resume" in text
```

- [ ] **Step 4：跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_resume_parser.py -v`
Expected: FAIL（無 app.intake.resume_parser）

- [ ] **Step 5：建立空的 `app/intake/__init__.py`，並實作 `app/intake/resume_parser.py`**

```python
"""履歷檔案攝取：PDF / DOCX / 純文字 → 純文字。"""
from __future__ import annotations

from io import BytesIO


def extract_text(data: bytes, filename: str) -> str:
    """依副檔名抽取純文字；未知副檔名以 UTF-8 文字處理。"""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return _extract_pdf(data)
    if name.endswith(".docx"):
        return _extract_docx(data)
    return data.decode("utf-8", errors="ignore")


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    parts = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(parts).strip()


def _extract_docx(data: bytes) -> str:
    from docx import Document

    doc = Document(BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs).strip()
```

- [ ] **Step 6：跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_resume_parser.py -v`
Expected: PASS（4 passed）

- [ ] **Step 7：Commit**

```bash
git add app/intake/__init__.py app/intake/resume_parser.py tests/test_resume_parser.py tests/fixtures/sample_resume.pdf requirements.txt
git commit -m "feat(m5): resume file intake (pdf/docx/text) + fixture"
```

---

### Task 3：履歷健檢 Agent（結構化 + 評分）

**Files:**
- Create: `app/agents/resume_eval.py`
- Test: `tests/test_resume_eval.py`

**Interfaces:**
- Consumes: `get_llm`（`app.llm`）、`Profile`/`ResumeAssessment`（Task 1）
- Produces: `structure_profile(resume_text: str) -> Profile`、`evaluate_resume(resume_text: str, profile: Profile) -> ResumeAssessment`

- [ ] **Step 1：寫失敗測試**（`tests/test_resume_eval.py`）

```python
from app.models import Profile, ResumeAssessment, ResumeIssue
from app.agents import resume_eval as mod
from tests.conftest import FakeLLM


def test_structure_profile_returns_profile(monkeypatch):
    canned = Profile(name="王小明", summary="後端工程師", skills=["Python"], raw_text="原文")
    monkeypatch.setattr(mod, "get_llm", lambda tier: FakeLLM(canned))
    result = mod.structure_profile("（履歷全文）")
    assert isinstance(result, Profile)
    assert result.name == "王小明"


def test_structure_profile_uses_cheap_tier(monkeypatch):
    seen = {}
    canned = Profile(name="x", summary="y", raw_text="z")

    def fake(tier):
        seen["tier"] = tier
        return FakeLLM(canned)

    monkeypatch.setattr(mod, "get_llm", fake)
    mod.structure_profile("text")
    assert seen["tier"] == "cheap"


def test_structure_profile_fills_raw_text_when_empty(monkeypatch):
    canned = Profile(name="王", summary="s", raw_text="")
    monkeypatch.setattr(mod, "get_llm", lambda tier: FakeLLM(canned))
    result = mod.structure_profile("完整履歷文字")
    assert result.raw_text == "完整履歷文字"


def test_evaluate_resume_returns_assessment(monkeypatch):
    canned = ResumeAssessment(
        overall_score=78, clarity_score=80, impact_score=70,
        ats_keyword_score=75, localization_score=85, completeness_score=80,
        summary="整體不錯", strengths=["技能清楚"],
        issues=[ResumeIssue(severity="medium", area="工作經歷", problem="缺量化", fix="加數字")],
    )
    monkeypatch.setattr(mod, "get_llm", lambda tier: FakeLLM(canned))
    result = mod.evaluate_resume("履歷全文", Profile(name="王", summary="s", raw_text="r"))
    assert isinstance(result, ResumeAssessment)
    assert result.overall_score == 78
    assert result.issues[0].severity == "medium"


def test_evaluate_resume_uses_deep_tier(monkeypatch):
    seen = {}
    canned = ResumeAssessment(
        overall_score=1, clarity_score=1, impact_score=1, ats_keyword_score=1,
        localization_score=1, completeness_score=1, summary="x",
    )

    def fake(tier):
        seen["tier"] = tier
        return FakeLLM(canned)

    monkeypatch.setattr(mod, "get_llm", fake)
    mod.evaluate_resume("t", Profile(name="a", summary="b", raw_text="c"))
    assert seen["tier"] == "deep"
```

- [ ] **Step 2：跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_resume_eval.py -v`
Expected: FAIL（無 app.agents.resume_eval）

- [ ] **Step 3：實作 `app/agents/resume_eval.py`**

```python
"""② 履歷健檢 Agent：把履歷全文結構化成 Profile，並做健檢評分。"""
from app.llm import get_llm
from app.models import Profile, ResumeAssessment

STRUCTURE_SYSTEM = (
    "你是履歷解析器。請從使用者提供的履歷全文中，抽取結構化欄位："
    "姓名(name)、一句話定位(summary)、技能清單(skills)、經歷條列(experiences)、"
    "學歷(education)、總年資(years_experience)、期望職務(preferred_roles)。"
    "raw_text 欄位請填入原始履歷全文。找不到的欄位留空或 null，不要捏造。"
)

EVAL_SYSTEM = (
    "你是資深台灣科技業招募顧問暨履歷健檢專家。請依台灣求職與 ATS 慣例，對這份履歷評分"
    "（每項 0-100）：整體(overall_score)、表達清晰度(clarity_score)、量化成果(impact_score)、"
    "ATS 關鍵字涵蓋(ats_keyword_score)、台灣履歷慣例符合度(localization_score)、完整度(completeness_score)。"
    "另外提供：一段總評(summary)、優點清單(strengths)、問題清單(issues，每項含 severity=high/medium/low、"
    "area 所在區塊、problem 問題、fix 可照做的具體修正)、以及 2-4 個改寫前後對照範例(rewrite_examples)。"
    "務實具體、不空泛，不要捏造未提供的經歷。全程使用繁體中文。"
)


def structure_profile(resume_text: str) -> Profile:
    """履歷全文 → 結構化 Profile（cheap 分層）。"""
    llm = get_llm("cheap").with_structured_output(Profile)
    profile = llm.invoke([("system", STRUCTURE_SYSTEM), ("human", resume_text)])
    if not profile.raw_text:
        profile.raw_text = resume_text
    return profile


def evaluate_resume(resume_text: str, profile: Profile) -> ResumeAssessment:
    """履歷健檢評分（deep 分層）。"""
    llm = get_llm("deep").with_structured_output(ResumeAssessment)
    human = (
        f"【履歷全文】\n{resume_text}\n\n"
        f"【已結構化資料】\n{profile.model_dump_json(indent=2)}"
    )
    return llm.invoke([("system", EVAL_SYSTEM), ("human", human)])
```

- [ ] **Step 4：跑測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_resume_eval.py -v`
Expected: PASS（5 passed）

- [ ] **Step 5：Commit**

```bash
git add app/agents/resume_eval.py tests/test_resume_eval.py
git commit -m "feat(m5): resume_eval agent (structure profile + health-check scoring)"
```

---

### Task 4：SSE 端點 `POST /api/resume/evaluate`

**Files:**
- Modify: `app/server.py`
- Test: `tests/test_server.py`（append）

**Interfaces:**
- Consumes: `extract_text`（Task 2）、`structure_profile`/`evaluate_resume`（Task 3）
- Produces: HTTP `POST /api/resume/evaluate`（multipart：`file` 檔案或 `resume_text` 文字）→ SSE 事件 `start / progress / profile / assessment / done`（空輸入時 `error`）

- [ ] **Step 1：寫失敗測試**（append 到 `tests/test_server.py`）

```python
def test_resume_evaluate_with_text(monkeypatch):
    from app.models import Profile, ResumeAssessment
    monkeypatch.setattr(server_mod, "structure_profile",
                        lambda text: Profile(name="王小明", summary="後端工程師", raw_text=text))
    monkeypatch.setattr(server_mod, "evaluate_resume",
                        lambda text, profile: ResumeAssessment(
                            overall_score=80, clarity_score=80, impact_score=80,
                            ats_keyword_score=80, localization_score=80,
                            completeness_score=80, summary="不錯"))
    client = TestClient(server_mod.app)
    r = client.post("/api/resume/evaluate", data={"resume_text": "我的履歷 Python"})
    assert r.status_code == 200
    events = _parse_sse(r.text)
    types = [e["type"] for e in events]
    assert types[0] == "start"
    assert "assessment" in types
    assert types[-1] == "done"
    assessment_ev = next(e for e in events if e["type"] == "assessment")
    assert assessment_ev["data"]["overall_score"] == 80


def test_resume_evaluate_empty_returns_error():
    client = TestClient(server_mod.app)
    r = client.post("/api/resume/evaluate", data={"resume_text": "   "})
    events = _parse_sse(r.text)
    assert any(e["type"] == "error" for e in events)
```

- [ ] **Step 2：跑測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_server.py -k resume_evaluate -v`
Expected: FAIL（404 / 無端點）

- [ ] **Step 3：實作端點**（修改 `app/server.py`）

(a) 在 import 區加入：

```python
from fastapi import FastAPI, File, Form, UploadFile
from app.intake.resume_parser import extract_text
from app.agents.resume_eval import structure_profile, evaluate_resume
```

（把既有 `from fastapi import FastAPI` 那行替換成上面第一行；另兩個 import 放在 `from app.graph import build_graph` 之後。）

(b) 在 `@app.get("/api/sample")` 之前加入新端點：

```python
@app.post("/api/resume/evaluate")
async def resume_evaluate(
    file: UploadFile | None = File(default=None),
    resume_text: str = Form(default=""),
):
    if file is not None:
        data = await file.read()
        text = extract_text(data, file.filename or "resume.txt")
    else:
        text = resume_text

    def gen():
        yield _sse({"type": "start"})
        if not text.strip():
            yield _sse({"type": "error", "message": "請提供履歷檔案或文字"})
            return
        yield _sse({"type": "progress", "step": "structure", "message": "解析履歷中…"})
        profile = structure_profile(text)
        yield _sse({"type": "profile", "data": profile})
        yield _sse({"type": "progress", "step": "evaluate", "message": "健檢評估中…"})
        assessment = evaluate_resume(text, profile)
        yield _sse({"type": "assessment", "data": assessment})
        yield _sse({"type": "done"})

    return StreamingResponse(gen(), media_type="text/event-stream")
```

- [ ] **Step 4：跑測試確認通過 + 全套**

Run: `.venv\Scripts\python.exe -m pytest tests/test_server.py -v`（既有 + 2 新測試全綠）
Run: `.venv\Scripts\python.exe -m pytest`（全套維持綠）

- [ ] **Step 5：Commit**

```bash
git add app/server.py tests/test_server.py
git commit -m "feat(m5): POST /api/resume/evaluate SSE endpoint (upload/paste -> assessment)"
```

---

### Task 5：前端骨架（Vite + React + TS + Tailwind）+ FastAPI 提供建置產物

**Files:**
- Create: `frontend/`（Vite 專案：`package.json`、`vite.config.ts`、`tailwind.config.js`、`postcss.config.js`、`index.html`、`src/main.tsx`、`src/index.css`、`src/App.tsx` 佔位）
- Create/Modify: `.gitignore`（忽略 `frontend/node_modules`、`frontend/dist`）
- Modify: `app/server.py`（`/` 優先提供 `frontend/dist`，否則回退既有 `app/web/index.html`；掛載 `/assets`）

**Interfaces:**
- Produces: 可 `npm run build` 出 `frontend/dist`；`uvicorn` 在 `/` 提供 React 應用

- [ ] **Step 1：建立 Vite 專案（從專案根）**

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

- [ ] **Step 2：安裝並設定 Tailwind v3**

```bash
npm install -D tailwindcss@3 postcss autoprefixer
npx tailwindcss init -p
```

設 `frontend/tailwind.config.js` 的 content：

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
```

把 `frontend/src/index.css` **整檔**改為：

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 3：設定 `frontend/index.html` 標題（含「求職」字樣）與語言**

把 `<html lang="en">` 改成 `<html lang="zh-Hant">`，`<title>...</title>` 改成：

```html
<title>台灣 AI 求職 Co-pilot</title>
```

- [ ] **Step 4：設定 dev proxy**（`frontend/vite.config.ts` 整檔）

```ts
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
})
```

- [ ] **Step 5：`frontend/src/App.tsx` 佔位內容**

```tsx
export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex items-center justify-center">
      <h1 className="text-2xl font-bold">台灣 AI 求職 Co-pilot（前端骨架就緒）</h1>
    </div>
  )
}
```

- [ ] **Step 6：建置**

```bash
npm run build
```

Expected: 成功產生 `frontend/dist/index.html` 與 `frontend/dist/assets/`。

- [ ] **Step 7：`.gitignore` 加入（若無則建立）**

```
frontend/node_modules/
frontend/dist/
```

- [ ] **Step 8：讓 FastAPI 提供建置產物**（修改 `app/server.py`）

(a) import 區加入：

```python
from fastapi.staticfiles import StaticFiles
```

(b) 在 `_ROOT = ...` 之後加：

```python
_FRONTEND_DIST = _ROOT / "frontend" / "dist"
if (_FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")
```

(c) 把既有 `index()` 改為優先提供 dist、否則回退：

```python
@app.get("/", response_class=HTMLResponse)
def index():
    dist_index = _FRONTEND_DIST / "index.html"
    if dist_index.exists():
        return dist_index.read_text(encoding="utf-8")
    return (_WEB_DIR / "index.html").read_text(encoding="utf-8")
```

- [ ] **Step 9：驗證**

Run: `.venv\Scripts\python.exe -m pytest tests/test_server.py::test_index_serves_html -v`
Expected: PASS（dist 已建置 → 提供 React index.html，含「求職」字樣）。
Run: `.venv\Scripts\python.exe -m pytest`
Expected: 全套綠。
手動：`.venv\Scripts\python.exe -m uvicorn app.server:app --port 8000` → 開 http://localhost:8000 看到骨架頁。

- [ ] **Step 10：Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/tailwind.config.js frontend/postcss.config.js frontend/index.html frontend/src app/server.py .gitignore
git commit -m "feat(m5): Vite+React+Tailwind frontend scaffold served by FastAPI"
```

---

### Task 6：履歷健檢頁（上傳/貼 → 串流 → 儀表板）

**Files:**
- Create: `frontend/src/types.ts`、`frontend/src/sse.ts`、`frontend/src/sampleResume.ts`
- Create: `frontend/src/components/ScoreRing.tsx`、`ScoreBars.tsx`、`IssueCard.tsx`、`RewriteCard.tsx`、`Dashboard.tsx`
- Modify: `frontend/src/App.tsx`（整檔覆寫成健檢頁）

**Interfaces:**
- Consumes: `POST /api/resume/evaluate`（Task 4）SSE 事件 `start/progress/profile/assessment/done/error`

- [ ] **Step 1：型別**（`frontend/src/types.ts`）

```ts
export interface ResumeIssue { severity: "high" | "medium" | "low"; area: string; problem: string; fix: string }
export interface ResumeRewrite { original: string; improved: string; why: string }
export interface ResumeAssessment {
  overall_score: number; clarity_score: number; impact_score: number;
  ats_keyword_score: number; localization_score: number; completeness_score: number;
  summary: string; strengths: string[]; issues: ResumeIssue[]; rewrite_examples: ResumeRewrite[];
}
export type SSEEvent =
  | { type: "start" }
  | { type: "progress"; step: string; message: string }
  | { type: "profile"; data: unknown }
  | { type: "assessment"; data: ResumeAssessment }
  | { type: "done" }
  | { type: "error"; message: string }
```

- [ ] **Step 2：SSE 讀取工具**（`frontend/src/sse.ts`）

```ts
export async function readSSE(resp: Response, onEvent: (ev: any) => void) {
  const reader = resp.body!.getReader()
  const dec = new TextDecoder()
  let buf = ""
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    let idx: number
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, idx)
      buf = buf.slice(idx + 2)
      const line = chunk.split("\n").find((l) => l.startsWith("data:"))
      if (line) onEvent(JSON.parse(line.slice(5).trim()))
    }
  }
}
```

- [ ] **Step 3：範例履歷**（`frontend/src/sampleResume.ts`）

```ts
export const SAMPLE_RESUME = `王小明
後端工程師 / Python

技能：Python、FastAPI、PostgreSQL、Docker、AWS
經歷：
- 在新創負責後端開發，維護 API 與資料庫
- 參與系統重構，改善效能
學歷：國立台灣大學 資訊工程學系
年資：3 年`
```

- [ ] **Step 4：元件**

`frontend/src/components/ScoreRing.tsx`（總分環形）：

```tsx
export function ScoreRing({ score }: { score: number }) {
  const r = 52, c = 2 * Math.PI * r
  const offset = c * (1 - score / 100)
  const color = score >= 80 ? "#059669" : score >= 60 ? "#d97706" : "#dc2626"
  return (
    <svg width="140" height="140" viewBox="0 0 140 140">
      <circle cx="70" cy="70" r={r} fill="none" stroke="#e2e8f0" strokeWidth="12" />
      <circle cx="70" cy="70" r={r} fill="none" stroke={color} strokeWidth="12"
        strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
        transform="rotate(-90 70 70)" />
      <text x="70" y="66" textAnchor="middle" fontSize="32" fontWeight="700" fill="#0f172a">{score}</text>
      <text x="70" y="90" textAnchor="middle" fontSize="13" fill="#64748b">/ 100</text>
    </svg>
  )
}
```

`frontend/src/components/ScoreBars.tsx`（五項分數長條）：

```tsx
const LABELS: Record<string, string> = {
  clarity_score: "表達清晰度", impact_score: "量化成果", ats_keyword_score: "ATS 關鍵字",
  localization_score: "台灣慣例", completeness_score: "完整度",
}
export function ScoreBars({ scores }: { scores: Record<string, number> }) {
  return (
    <div className="space-y-3">
      {Object.entries(LABELS).map(([k, label]) => {
        const v = scores[k] ?? 0
        const color = v >= 80 ? "bg-emerald-500" : v >= 60 ? "bg-amber-500" : "bg-rose-500"
        return (
          <div key={k}>
            <div className="flex justify-between text-sm mb-1"><span>{label}</span><span className="font-medium">{v}</span></div>
            <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
              <div className={`h-full ${color} rounded-full`} style={{ width: `${v}%` }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}
```

`frontend/src/components/IssueCard.tsx`：

```tsx
import type { ResumeIssue } from "../types"
const SEV: Record<string, { label: string; cls: string }> = {
  high: { label: "高", cls: "bg-rose-100 text-rose-700" },
  medium: { label: "中", cls: "bg-amber-100 text-amber-700" },
  low: { label: "低", cls: "bg-slate-100 text-slate-600" },
}
export function IssueCard({ issue }: { issue: ResumeIssue }) {
  const sev = SEV[issue.severity] ?? SEV.low
  return (
    <div className="border rounded-lg p-4 bg-white">
      <div className="flex items-center gap-2 mb-1">
        <span className={`text-xs px-2 py-0.5 rounded-full ${sev.cls}`}>嚴重度：{sev.label}</span>
        <span className="text-sm font-medium text-slate-500">{issue.area}</span>
      </div>
      <p className="text-sm text-slate-800">{issue.problem}</p>
      <p className="text-sm text-emerald-700 mt-1">建議：{issue.fix}</p>
    </div>
  )
}
```

`frontend/src/components/RewriteCard.tsx`：

```tsx
import type { ResumeRewrite } from "../types"
export function RewriteCard({ rw }: { rw: ResumeRewrite }) {
  return (
    <div className="border rounded-lg p-4 bg-white space-y-2">
      <div className="text-sm"><span className="text-rose-600 font-medium">原句：</span><span className="line-through text-slate-500">{rw.original}</span></div>
      <div className="text-sm"><span className="text-emerald-600 font-medium">改寫：</span><span className="text-slate-800">{rw.improved}</span></div>
      <div className="text-xs text-slate-500">原因：{rw.why}</div>
    </div>
  )
}
```

`frontend/src/components/Dashboard.tsx`：

```tsx
import type { ResumeAssessment } from "../types"
import { ScoreRing } from "./ScoreRing"
import { ScoreBars } from "./ScoreBars"
import { IssueCard } from "./IssueCard"
import { RewriteCard } from "./RewriteCard"

export function Dashboard({ a }: { a: ResumeAssessment }) {
  return (
    <div className="space-y-6">
      <div className="grid md:grid-cols-2 gap-6 items-center bg-white border rounded-xl p-6">
        <div className="flex items-center gap-6">
          <ScoreRing score={a.overall_score} />
          <div>
            <h2 className="text-lg font-bold mb-1">履歷健檢總分</h2>
            <p className="text-sm text-slate-600">{a.summary}</p>
          </div>
        </div>
        <ScoreBars scores={a as unknown as Record<string, number>} />
      </div>

      {a.strengths.length > 0 && (
        <section>
          <h3 className="font-semibold mb-2">✅ 優點</h3>
          <div className="grid md:grid-cols-2 gap-2">
            {a.strengths.map((s, i) => (
              <div key={i} className="text-sm bg-emerald-50 border border-emerald-100 rounded-lg p-3">{s}</div>
            ))}
          </div>
        </section>
      )}

      {a.issues.length > 0 && (
        <section>
          <h3 className="font-semibold mb-2">⚠️ 可改進項目</h3>
          <div className="grid md:grid-cols-2 gap-3">
            {a.issues.map((it, i) => <IssueCard key={i} issue={it} />)}
          </div>
        </section>
      )}

      {a.rewrite_examples.length > 0 && (
        <section>
          <h3 className="font-semibold mb-2">✍️ 改寫範例</h3>
          <div className="grid md:grid-cols-2 gap-3">
            {a.rewrite_examples.map((rw, i) => <RewriteCard key={i} rw={rw} />)}
          </div>
        </section>
      )}
    </div>
  )
}
```

- [ ] **Step 5：`frontend/src/App.tsx`（整檔覆寫）**

```tsx
import { useState } from "react"
import type { ResumeAssessment } from "./types"
import { readSSE } from "./sse"
import { SAMPLE_RESUME } from "./sampleResume"
import { Dashboard } from "./components/Dashboard"

export default function App() {
  const [text, setText] = useState("")
  const [status, setStatus] = useState("")
  const [busy, setBusy] = useState(false)
  const [assessment, setAssessment] = useState<ResumeAssessment | null>(null)
  const [error, setError] = useState("")

  async function evaluate(form: FormData) {
    setBusy(true); setError(""); setAssessment(null); setStatus("上傳中…")
    try {
      const resp = await fetch("/api/resume/evaluate", { method: "POST", body: form })
      await readSSE(resp, (ev) => {
        if (ev.type === "progress") setStatus(ev.message)
        else if (ev.type === "assessment") setAssessment(ev.data as ResumeAssessment)
        else if (ev.type === "error") setError(ev.message)
        else if (ev.type === "done") setStatus("完成 ✅")
      })
    } catch (e) {
      setError("連線發生問題，請確認伺服器是否啟動。")
    } finally {
      setBusy(false)
    }
  }

  function onSubmitText() {
    if (!text.trim()) { setError("請先貼上或載入履歷文字"); return }
    const form = new FormData()
    form.append("resume_text", text)
    evaluate(form)
  }

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (!f) return
    const form = new FormData()
    form.append("file", f)
    evaluate(form)
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <div className="max-w-5xl mx-auto p-6">
        <header className="mb-6">
          <h1 className="text-2xl font-bold">台灣 AI 求職 Co-pilot</h1>
          <p className="text-slate-500">上傳或貼上你的履歷，AI 幫你健檢評分並給出具體改進建議。</p>
        </header>

        <div className="bg-white border rounded-xl p-5 mb-6">
          <textarea
            className="w-full border rounded-lg p-3 text-sm h-40"
            placeholder="貼上履歷文字…"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="flex flex-wrap gap-2 mt-3 items-center">
            <button onClick={onSubmitText} disabled={busy}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm disabled:opacity-50">
              開始健檢
            </button>
            <button onClick={() => setText(SAMPLE_RESUME)} disabled={busy}
              className="px-4 py-2 bg-slate-200 rounded-lg text-sm">載入範例履歷</button>
            <label className="px-4 py-2 bg-slate-200 rounded-lg text-sm cursor-pointer">
              上傳檔案（PDF/DOCX/TXT）
              <input type="file" accept=".pdf,.docx,.txt" className="hidden" onChange={onFile} disabled={busy} />
            </label>
            {status && <span className="text-sm text-slate-500">{status}</span>}
          </div>
          {error && <p className="text-sm text-rose-600 mt-2">{error}</p>}
        </div>

        {assessment && <Dashboard a={assessment} />}
      </div>
    </div>
  )
}
```

- [ ] **Step 6：建置確認**

```bash
cd frontend
npm run build
```

Expected: 成功（無 TypeScript 錯誤）。

- [ ] **Step 7：全套後端測試 + 手動驗證**

Run（從專案根）: `.venv\Scripts\python.exe -m pytest`
Expected: 全套綠。
手動：啟 `uvicorn app.server:app --port 8000` → 開 http://localhost:8000 → 「載入範例履歷」→「開始健檢」→ 看到串流進度與**儀表板**（總分環、五項長條、優缺點卡、改寫範例），非 JSON。

- [ ] **Step 8：Commit**

```bash
git add frontend/src
git commit -m "feat(m5): resume health-check page (upload/paste -> streamed dashboard)"
```

---

## 自我檢查（writing-plans self-review）

- **Spec 覆蓋**：M5 spec 的「履歷攝取 / resume_eval / ResumeAssessment / /api/resume/evaluate / Vite 前端骨架 / 健檢儀表板 / pypdf+python-docx」皆有對應任務。✓
- **型別一致**：`extract_text(bytes,str)`、`structure_profile(str)->Profile`、`evaluate_resume(str,Profile)->ResumeAssessment`、前端 `ResumeAssessment` 欄位與後端模型欄位逐一對應。✓
- **無 placeholder**：每個程式步驟均含完整程式碼與預期輸出。✓
- **既有不破**：未改 graph/既有 agent；`index()` 回退邏輯確保未建置 dist 時 `test_index_serves_html` 仍綠。✓
```