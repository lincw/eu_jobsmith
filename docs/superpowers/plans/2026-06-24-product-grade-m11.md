# M11 — 差異化 wow + 收尾 Implementation Plan

> **For agentic workers:** 由本 session inline 執行（沿用 M8–M10：後端 pytest TDD、前端 `npm run build` 閘門、每任務 commit、milestone 結束對抗式審查）。

**Goal:** 在 M8–M10 基礎上加上側欄 shell、多輪面試模擬、歷史投遞包、職缺無上限分頁、技能缺口分析、記憶/個人化、公司職缺查詢，把產品收尾到作品集級。

**Architecture:** 前端改「左 rail + 右內容」shell；新增 sqlite（`data/app.sqlite`）存歷史與記憶；新 agent 模組（interview_sim / skill_gap / company_jobs）走既有 `app/llm.py` 分層與 `research_structured`（claude_cli WebSearch）；新端點皆同步 `def`。

**Tech Stack:** FastAPI + sqlite(標準庫) + LangGraph(既有) + httpx/bs4(既有)；React 19 + TS + Tailwind v3 + lucide-react（既有原語）。

## Global Constraints

- 介面 zh-Hant；單人本機、無登入。
- 串流/查詢端點用同步 `def`（避免 claude_cli subprocess 阻塞）。
- 前端閘門：`cd frontend && npm run build` 成功；`import type`；**圖示一律 lucide（走 `ui/icons.ts`），嚴禁 emoji 作功能圖示**；走 M10 原語（Card/Button/Badge/EmptyState/Skeleton）與 brand token。
- 不破壞既有：自動找職缺/履歷健檢/投遞包工作台/後端切換/優雅降級/telemetry/人工核可/JD 抓取/匯出/4 來源。
- 新依賴只用純 Python；sqlite 用標準庫；`COPILOT_APP_DB` 可覆寫（測試 `:memory:`），預設 `data/app.sqlite`。
- LLM 經 `app/llm.py`；成本記 telemetry。上網查證走 `research_structured`（claude_cli）；非 CLI 後端優雅降級。
- 每任務結束 `git commit`。

## File Structure

- `frontend/src/ui/Sidebar.tsx`（新）— 左側 rail（圖示+文字）
- `frontend/src/App.tsx`（改）— rail + 內容區 shell
- `frontend/src/components/BackendSelector.tsx`（改）— 頂部「本機 CLI」chip，只露 claude_cli/codex_cli
- `app/store/db.py`（新）— sqlite 連線；`app/store/history.py`（新）；`app/store/memory.py`（新）
- `app/agents/interview_sim.py`（新）；`app/agents/skill_gap.py`（新）；`app/agents/company_jobs.py`（新）
- `app/models.py`（改）— InterviewQuestion/AnswerFeedback/InterviewSummary/SkillGapReport
- `app/server.py`（改）— 新端點；`app/state.py`（改）— preferences
- `app/agents/job_search.py`（改）— rank_jobs 上限
- `frontend/src/views/`（新）InterviewView、HistoryView；（改）JobSearchView、PipelineView、ResumeHealthView
- 對應 `tests/test_*.py`

---

## Task 0：App shell（側欄 rail + 本機 CLI chip）

**Files:** Create `frontend/src/ui/Sidebar.tsx`；Modify `frontend/src/App.tsx`、`frontend/src/components/BackendSelector.tsx`、`frontend/src/ui/icons.ts`

**Interfaces — Produces:** `<Sidebar active tab onSelect items>`；App 改 `flex` shell（rail 寬 ~210px + `<main flex-1>`）；分頁 id 擴充為 `search|resume|pipeline|interview|history`。

- [ ] 在 `ui/icons.ts` 增匯出：`Compass, FileChartColumn, Workflow, MessagesSquare, Archive, Settings2, ChevronLeft, ChevronRight`（lucide）。
- [ ] 建 `Sidebar.tsx`：垂直清單，每項 `{id,label,icon}`；active 用 `bg-brand-600 text-white`、其餘 `text-slate-500 hover:bg-slate-100`；頂部放 `<Brand size="sm">`；底部「個人化」項；`focus-visible:ring`。寬 `w-52`，`shrink-0`，`border-r`，整段 `no-print`。
- [ ] `App.tsx`：外層改 `flex min-h-screen`；左 `<Sidebar>`，右 `<main className="flex-1 min-w-0"><div className="max-w-6xl mx-auto px-4 sm:px-6 py-6">`；頂部列 `<BackendSelector>` 靠右；保留三分頁「全掛載只切顯示」並加 interview/history 兩個容器。行動裝置：`hidden md:flex` rail + 上方放一條水平 tab（sm 顯示）或漢堡（簡化：sm 時 rail 變頂部 segmented，沿用 M10 樣式）。
- [ ] `BackendSelector.tsx`：改 chip 樣式（圓角 pill、`Cpu` 圖示 + 「本機 CLI · {label}」+ ChevronDown），下拉**只列 `claude_cli`/`codex_cli`**（過濾掉 anthropic）；保留 `/api/backend` 邏輯；tooltip（`title`）說明模型分層。
- [ ] 驗證 `npm run build` 綠；commit `feat(m11): T0 側欄 shell + 本機 CLI chip`。

---

## Task 1：多輪面試模擬器

**Files:** Create `app/agents/interview_sim.py`、`tests/test_interview_sim.py`、`frontend/src/views/InterviewView.tsx`；Modify `app/models.py`、`app/server.py`、`frontend/src/App.tsx`（接分頁）

**Interfaces — Produces:**
- models：`InterviewQuestion{category:str, question:str}`、`AnswerFeedback{score:int, strengths:list[str], improvements:list[str], model_answer:str}`、`InterviewSummary{overall_score:int, summary:str, advice:list[str]}`。
- `generate_questions(jd:str, profile:Profile, n:int=6)->list[InterviewQuestion]`
- `evaluate_answer(question:str, answer:str, jd:str, profile:Profile)->AnswerFeedback`
- `summarize(jd:str, transcript:list[dict])->InterviewSummary`（transcript 元素 `{question,answer}`）
- 端點：`POST /api/interview/start`→`{questions:[...]}`；`POST /api/interview/answer`→`AnswerFeedback`；`POST /api/interview/summary`→`InterviewSummary`。

- [ ] **測試先寫** `tests/test_interview_sim.py`（mock `get_llm` 用 `tests.conftest.FakeLLM`）：
```python
from app.agents import interview_sim as iv
from app.models import Profile, InterviewQuestion, AnswerFeedback, InterviewSummary
from tests.conftest import FakeLLM

def _p(): return Profile(name="王", summary="後端", raw_text="…")

def test_generate_questions(monkeypatch):
    canned = [InterviewQuestion(category="技術", question="介紹一個你做過的系統")]
    monkeypatch.setattr(iv, "get_llm", lambda tier: FakeLLM(canned))
    qs = iv.generate_questions("AI 工程師 JD", _p(), n=1)
    assert qs and qs[0].question

def test_evaluate_answer(monkeypatch):
    fb = AnswerFeedback(score=80, strengths=["具體"], improvements=["量化"], model_answer="…")
    monkeypatch.setattr(iv, "get_llm", lambda tier: FakeLLM(fb))
    out = iv.evaluate_answer("題", "答", "JD", _p())
    assert out.score == 80 and out.improvements

def test_summarize(monkeypatch):
    s = InterviewSummary(overall_score=78, summary="整體不錯", advice=["多準備系統設計"])
    monkeypatch.setattr(iv, "get_llm", lambda tier: FakeLLM(s))
    out = iv.summarize("JD", [{"question":"q","answer":"a"}])
    assert out.overall_score == 78
```
- [ ] 跑測試 FAIL（模組未建）。
- [ ] `app/models.py` 加三個 model（`InterviewQuestion/AnswerFeedback/InterviewSummary`，欄位含預設值=空 list/0/""）。
- [ ] 實作 `interview_sim.py`：各函式用 `get_llm("standard").with_structured_output(Model)`；`generate_questions` 回 `list[InterviewQuestion]`（用包裝 model `InterviewQuestionList{items:list[InterviewQuestion]}` 取 `.items`，與既有 structured 慣例一致）；system 提示：依 JD + 履歷出 n 題（技術/行為/台灣特有混合）、`evaluate_answer` 給分與優缺與示範答、`summarize` 給總分與建議。
- [ ] 跑測試 PASS：`.\.venv\Scripts\python -m pytest tests/test_interview_sim.py -q`。
- [ ] `server.py` 加三端點（同步 def；body 用 Pydantic：`InterviewStartBody{jd_text, profile:dict|None}` 等；profile 經 `_resolve_profile` 同款解析；try/except→友善 SSE/JSON error）。每次呼叫前 `telemetry.begin_node`/`end_node` 包起來記成本（沿用 `_safe` 思路，或直接 begin/end 包住）。
- [ ] `InterviewView.tsx`：JD textarea（或「從我的投遞包帶入」）→「開始面試」`POST start` → 逐題顯示；作答 textarea + 送出 `POST answer` → 回饋卡（`ScoreRing` + 優點(emerald Badge)/可改進(amber)/示範答法）→ 下一題（進度 `Qn/N`）→ 末題後「看總評」`POST summary` → 總評卡。用原語 + lucide（`MessagesSquare`）。
- [ ] `App.tsx` 接 `interview` 分頁。
- [ ] `npm run build` 綠 + 後端測試綠；commit `feat(m11): T1 多輪面試模擬器`。

---

## Task 2：歷史紀錄／我的投遞包

**Files:** Create `app/store/db.py`、`app/store/history.py`、`tests/test_history.py`、`frontend/src/views/HistoryView.tsx`；Modify `app/server.py`、`frontend/src/App.tsx`

**Interfaces — Produces:**
- `app/store/db.py`：`get_conn()->sqlite3.Connection`（讀 `COPILOT_APP_DB`，預設 `data/app.sqlite`，`check_same_thread=False`）；`init_db()` 建表（packages、user_memory）。
- `app/store/history.py`：`save_package(final_state:dict)->int`、`list_packages()->list[dict]`、`get_package(pid:int)->dict|None`、`delete_package(pid:int)->None`。
- 端點：`GET /api/history`→`[{id,created_at,job_title,company,match_score}]`；`GET /api/history/{id}`→完整；`DELETE /api/history/{id}`。

- [ ] **測試先寫** `tests/test_history.py`（conftest 已設 `COPILOT_APP_DB=:memory:`，見下步）：
```python
from app.store import history

def _state():
    return {"parsed_job":{"title":"AI 工程師","company":"未來智能"},
            "match_report":{"score":82},
            "tailored_resume":{"summary":"後端","bullets":["建 RAG"]},
            "cover_letter":{"subject":"應徵","body":"您好"},
            "interview_kit":{"technical_questions":["q"]},
            "critique":{"overall_pass":True}}

def test_save_and_get(tmp_path, monkeypatch):
    pid = history.save_package(_state())
    rows = history.list_packages()
    assert any(r["id"]==pid and r["company"]=="未來智能" and r["match_score"]==82 for r in rows)
    full = history.get_package(pid)
    assert full["package"]["tailored_resume"]["summary"]=="後端"

def test_delete(tmp_path):
    pid = history.save_package(_state())
    history.delete_package(pid)
    assert history.get_package(pid) is None
```
- [ ] `tests/conftest.py` 加 `os.environ.setdefault("COPILOT_APP_DB", ":memory:")`（在 import app 前）。注意 `:memory:` 每連線獨立——`db.get_conn()` 對 `:memory:` 需用單例連線（module-level cache）讓同程序共用同一 in-memory DB。
- [ ] 跑測試 FAIL。
- [ ] 實作 `db.py`（單例 conn for `:memory:`；檔案型則每次連線；啟動 `init_db()`）+ `history.py`（save 取 parsed_job/match 摘要欄位 + 整包 json.dumps；list 回摘要；get 回 `{...meta, package: json.loads}`）。
- [ ] 跑測試 PASS。
- [ ] `server.py`：(a) 加 `init_db()` 於啟動；(b) `_stream` 終局（`snapshot.next` 為空且有成品）後呼 `history.save_package(serialize(final_state))`——用 `GRAPH.get_state(config).values` 取最終 state、`serialize_update` 轉可 JSON；(c) 加三端點。
- [ ] `HistoryView.tsx`：`GET /api/history` 列清單（Card：職稱/公司/`ScoreRing` 小/日期 + 刪除 `Trash2`）；點開 `GET /api/history/{id}` 用既有 `Documents` 卡唯讀呈現 + 下載 Word/列印（重用）+「重新開啟」(帶回 pipeline via App 的 pickJob/seed)；空狀態 `EmptyState`（`Archive`）。
- [ ] `App.tsx` 接 `history` 分頁。
- [ ] `npm run build` + 後端測試綠；commit `feat(m11): T2 歷史紀錄/我的投遞包`。

---

## Task 3：推薦職缺無上限 + 分頁

**Files:** Modify `app/agents/job_search.py:63-85`、`app/server.py`(jobs_auto top_k)、`frontend/src/views/JobSearchView.tsx`、`tests/test_job_search.py`(或既有測試檔)

**Interfaces:** `rank_jobs(profile, jobs, top_k:int|None=None)`—`None`=不截斷（回全部排序）；為控 prompt，內部送 LLM 排序的職缺上限 `_RANK_INPUT_MAX=50`（超過先截）。

- [ ] **測試**：`rank_jobs` 給 20 筆、`top_k=None` → 回 20 筆（不截在 12）；給 60 筆 → LLM 輸入截在 50 但回傳不報錯。（mock get_llm 回對應 index 排序。）
```python
def test_rank_jobs_no_cap(monkeypatch):
    jobs = [JobPosting(source="x",title=f"j{i}",company="c",url=f"u{i}") for i in range(20)]
    monkeypatch.setattr(js,"get_llm",lambda tier: FakeRanker(len(jobs)))  # 回 0..n-1 排序
    out = js.rank_jobs(_profile(), jobs, top_k=None)
    assert len(out) == 20
```
- [ ] 跑 FAIL（目前截 12）。
- [ ] 改 `rank_jobs`：`top_k=None` 不做 `[:top_k]`；加 `_RANK_INPUT_MAX` 截 LLM 輸入。`server.py` jobs_auto 改 `rank_jobs(profile, all_jobs, top_k=None)`；每來源 `search_all(q, limit=15)`、查詢用 `queries[:3]` 擴池。
- [ ] 跑 PASS。
- [ ] `JobSearchView.tsx`：加 `page` state；`const PAGE=8`；顯示 `jobs.slice((page-1)*PAGE, page*PAGE)`；底部分頁列（上一頁/頁碼/下一頁，用 `ChevronLeft/Right`）；切搜尋時 `setPage(1)`。
- [ ] `npm run build` + 測試綠；commit `feat(m11): T3 職缺無上限 + 分頁`。

---

## Task 4：技能缺口市場分析

**Files:** Create `app/agents/skill_gap.py`、`tests/test_skill_gap.py`；Modify `app/models.py`、`app/server.py`(jobs_auto 發 skill_gap)、`frontend/src/views/JobSearchView.tsx`、`frontend/src/types.ts`

**Interfaces — Produces:** `SkillGapReport{top_demand:list[dict], your_gaps:list[dict], have:list[str]}`（dict=`{skill,count}`）；`analyze_skill_gap(profile:Profile, jobs:list[JobPosting])->SkillGapReport`（純函式、無 LLM）。

- [ ] **測試先寫** `tests/test_skill_gap.py`：
```python
from app.agents.skill_gap import analyze_skill_gap
from app.models import Profile, JobPosting

def test_gap_and_demand():
    jobs = [JobPosting(source="x",title="t",company="c",url="u",requirements=["Python","LLM"]),
            JobPosting(source="x",title="t",company="c",url="u2",requirements=["Python","Docker"])]
    prof = Profile(name="a", summary="", skills=["Python"], raw_text="")
    rep = analyze_skill_gap(prof, jobs)
    demand = {d["skill"]: d["count"] for d in rep.top_demand}
    assert demand["Python"] == 2
    gaps = {g["skill"] for g in rep.your_gaps}
    assert "LLM" in gaps and "Python" not in gaps   # 已具備不算缺口
```
- [ ] 跑 FAIL。
- [ ] 確認 `Profile` 有 `skills` 欄位（若無則改用既有欄位；查 `app/models.py`）。實作 `analyze_skill_gap`：彙整 jobs 的 `requirements`（小寫正規化比對、保留原字串顯示）算 count；profile 技能集合→have；需求中 not in have 者依 count 排序為 your_gaps；top_demand=全部需求依 count 排序取前 N(如 15)。`SkillGapReport` 加進 models。
- [ ] 跑 PASS。
- [ ] `server.py` jobs_auto：排序後 `rep = analyze_skill_gap(profile, all_jobs)`，發 `yield _sse({"type":"skill_gap","data": rep.model_dump()})`（在 jobs 事件後）。
- [ ] `JobSearchView.tsx`：接 `skill_gap` 事件存 state；結果頁上方一張「技能缺口分析」Card——你的缺口（rose `Badge`，附 `×count`）+ 市場熱門（重用 `ScoreBars` 風格的長條，依 count 正規化）。`types.ts` 加 `SkillGapReport`。
- [ ] `npm run build` + 測試綠；commit `feat(m11): T4 技能缺口市場分析`。

---

## Task 5：Agent 記憶／個人化

**Files:** Create `app/store/memory.py`、`tests/test_memory.py`、`frontend/src/components/PreferencesPanel.tsx`；Modify `app/server.py`、`app/state.py`、`app/agents/{resume,cover_letter,interview}.py`、`frontend/src/App.tsx`、`frontend/src/types.ts`

**Interfaces — Produces:**
- `app/store/memory.py`：`get_memory()->dict`（`{profile:dict|None, preferences:dict}`）、`save_profile(profile:dict)`、`save_preferences(prefs:dict)`。
- `CopilotState` 加 `preferences: dict | None`；resume/cover/interview agent 簽名加 `preferences: dict | None = None`，併入 system 提示。
- 端點：`GET /api/memory`、`POST /api/memory`（`{preferences}`）。

- [ ] **測試先寫** `tests/test_memory.py`（`:memory:` DB）：
```python
from app.store import memory
def test_profile_roundtrip():
    memory.save_profile({"name":"王","raw_text":"x"})
    assert memory.get_memory()["profile"]["name"]=="王"
def test_preferences_roundtrip():
    memory.save_preferences({"tone":"自信","emphasize_skills":["LLM"]})
    assert memory.get_memory()["preferences"]["tone"]=="自信"
```
- [ ] 跑 FAIL → 實作 `memory.py`（user_memory 單列 upsert）→ 跑 PASS。
- [ ] `/api/jobs/auto`、`/api/resume/evaluate` 解析出 profile 後呼 `memory.save_profile(profile.model_dump())`（try/except 不影響主流程）。
- [ ] `state.py` 加 `preferences`；`RunBody` 加 `preferences: dict|None=None`；`run()` 初始 state 帶入；resume/cover/interview node 把 `state.get("preferences")` 傳給 agent；agent 在 system 提示加「依偏好：語氣 X、強調技能 Y、目標年資 Z」（preferences 為 None 則維持原行為）。對應更新這些 agent 的測試 mock（加 preferences 參數預設）。
- [ ] `GET/POST /api/memory` 端點。
- [ ] 前端：App 啟動 `GET /api/memory` → 有 profile 則 `setProfile`（投遞包工作台不再示警）；`PreferencesPanel.tsx`（從個人化分頁/面板編輯偏好，`POST /api/memory`）；run 時把 preferences 併入 `/api/run` body。`types.ts` 加 `Preferences`。
- [ ] `npm run build` + 後端全套測試綠；commit `feat(m11): T5 記憶/個人化`。

---

## Task 6：公司職缺查詢

**Files:** Create `app/agents/company_jobs.py`、`tests/test_company_jobs.py`；Modify `app/server.py`、`frontend/src/views/JobSearchView.tsx`、`frontend/src/types.ts`

**Interfaces — Produces:** `find_company_jobs(company:str, profile:Profile|None=None)->list[JobPosting]`（A：`search_all(company)` 過濾 company 模糊相符；B：`research_structured(JobPostingList, ...)` claude_cli WebSearch 找官網 careers，source="careers"；合併去重 by url/(title+company)）。

- [ ] **測試先寫** `tests/test_company_jobs.py`：
```python
from app.agents import company_jobs as cj
from app.models import JobPosting, SearchResult

def test_merges_boards_and_careers(monkeypatch):
    monkeypatch.setattr(cj,"search_all", lambda kw, limit=15:[SearchResult(source="104",
        jobs=[JobPosting(source="104",title="AI 工程師",company="未來智能",url="u1"),
              JobPosting(source="104",title="PM",company="別家",url="u2")])])
    class L: jobs=[JobPosting(source="careers",title="ML",company="未來智能",url="https://futai.com/jobs/ml")]
    monkeypatch.setattr(cj,"research_structured", lambda *a, **k: L())
    out = cj.find_company_jobs("未來智能")
    titles = {j.title for j in out}
    assert "AI 工程師" in titles and "ML" in titles
    assert "PM" not in titles                 # 公司不符被濾掉

def test_careers_skipped_when_unsupported(monkeypatch):
    monkeypatch.setattr(cj,"search_all", lambda kw, limit=15:[SearchResult(source="104",
        jobs=[JobPosting(source="104",title="AI",company="未來智能",url="u1")])])
    monkeypatch.setattr(cj,"research_structured", lambda *a, **k: None)  # 非 CLI 後端
    out = cj.find_company_jobs("未來智能")
    assert len(out) == 1 and out[0].source == "104"
```
- [ ] 跑 FAIL → 實作（含包裝 model `JobPostingList{items:list[JobPosting]}` 給 research_structured；company 模糊比對＝雙向 `in` 或正規化相等；research_structured 回 None/拋錯則只回 boards）→ 跑 PASS。
- [ ] `server.py` 加 `POST /api/company/jobs`（SSE：progress→jobs→done；try/except 友善 error）。
- [ ] `JobSearchView.tsx`：頂部模式切換「依履歷找 / 依公司找」；後者輸入公司名 + 「查公司職缺」→ 列出（來源 Badge：官網/104/LinkedIn…，官網用 `Building2`），可「產生投遞包」。`types.ts` 重用 JobPosting。
- [ ] `npm run build` + 後端測試綠；commit `feat(m11): T6 公司職缺查詢`。

---

## 收尾

- [ ] 全套後端測試綠：`.\.venv\Scripts\python -m pytest -q`。
- [ ] `npm run build` 最終綠；`git status` 確認 `data/app.sqlite*` 已 gitignore（加入 .gitignore）。
- [ ] 對抗式審查 workflow（可用性/a11y/RWD/TS/後端安全/資料流回歸 + 新 sqlite 並發）→ 修 Critical/Important。
- [ ] 使用者 `! D:\Multi-Agent\run.bat` 驗收。

## Self-Review

- 規格涵蓋：⓪shell→T0、①面試→T1、②歷史→T2、③分頁→T3、④技能缺口→T4、⑤記憶→T5、⑥公司職缺→T6 ✓
- 依賴：純 Python + sqlite 標準庫；lucide（既有）✓ 不引入新系統依賴。
- 型別一致：models 三件（interview）、SkillGapReport、JobPostingList 包裝；store 三模組 get/save/list/delete 命名一致 ✓
- 風險：`:memory:` DB 需單例連線（已於 T2 註明）；preferences 為 None 維持原行為（不破壞既有測試，但需更新 agent mock 簽名）✓
- .gitignore 需加 `data/app.sqlite*`（收尾步驟）。
