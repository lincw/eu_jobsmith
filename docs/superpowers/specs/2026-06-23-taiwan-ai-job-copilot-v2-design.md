# 台灣 AI 求職 Co-pilot — v2 設計（產品化轉向）

> 延續並修訂 `2026-06-23-taiwan-ai-job-copilot-design.md`（v1）。v1 的 supervisor + 8 agent
> 反思迴圈、human-in-the-loop、模型分層、可抽換 LLM 後端（M1–M4，已併入 master）全部保留。
> 本文件只描述 v2 新增與變更的部分。

## 為什麼要 v2

v1 的入口是「貼一則 JD → 產生投遞包」，且 M4 前端把成品直接 dump 成 JSON。實際使用者更想要的是
**以求職者為中心**的流程，而且要有產品級的外觀與正式文件輸出，JSON dump 不算成熟產品。

**三個核心轉變：**
1. **入口改成上傳履歷**：上傳 PDF/貼文字 → AI 健檢評分＋具體改進建議。
2. **加入職缺探索**：依履歷在台灣常用平台找適合職缺並排序（104 / Cake / Yourator 關鍵字搜尋；
   LinkedIn 貼網址/深連結；通用「貼任意網址」抽單頁）。
3. **產品級前端 + 正式文件輸出**：用 Vite + React + Tailwind + shadcn/ui 重做前端；所有成品
   渲染成正式排版文件、可匯出 PDF；不再出現原始 JSON。

## 完整使用者流程

```
上傳/貼履歷
  → ① 履歷攝取（PDF/DOCX/文字 → 結構化 Profile）
  → ② 履歷健檢（ResumeAssessment：總分＋分項＋優缺點＋改寫範例）  ← M5 的主交付
  → ③ 依履歷找適合職缺並排序（104/Cake/Yourator 搜尋 + 貼網址）   ← M6
  → 使用者選定一則職缺
  → ④ 既有投遞包流程（match → 公司情報 → 客製履歷 ∥ 求職信 ∥ 面試 → 品管 → 人工核可）
  → ⑤ 全部渲染成正式文件 + 匯出 PDF                                ← M7
```

## 合規與法律立場（重要）

- **定位**：個人／作品集用途，不對外當公開付費 SaaS 部署。
- **104 / Cake / Yourator 搜尋**：走各站「前端自己呼叫的搜尋 JSON 端點」，**低頻率、個人使用規模**，
  帶合理 User-Agent，**被擋（非 200／驗證牆／空回應）就優雅降級**回傳空清單 + `blocked=True` 旗標，
  不重試硬衝。
- **不做反偵測軍備競賽**：不做代理輪換、不破 CAPTCHA、不繞登入牆。對個人作品集沒必要，面試也是減分。
- **LinkedIn**：反爬最兇、法律最敏感 → **不爬整頁**。只做（a）貼單一職缺網址抽取、（b）用關鍵字產生
  LinkedIn 搜尋深連結讓使用者自己一鍵開過去。
- 每個 source 隔離成獨立模組；任一 source 壞掉不影響其他功能與既有投遞包流程。
- README 與 UI 會標明資料來源與「個人使用、遵守各站 ToS 風險自負」。

## 架構：既有 + 新增

既有（不動）：`app/agents/*`、`app/graph.py`、`app/llm.py`、`app/settings.py`、SSE server 的投遞包流程。

新增模組：

| 模組 | 職責 |
|---|---|
| `app/intake/resume_parser.py` | PDF（pypdf）/DOCX（python-docx）/純文字 → 純文字；再交 LLM 結構化成 `Profile` |
| `app/agents/resume_eval.py` | LLM agent：`Profile` + 原始履歷文字 → `ResumeAssessment`（台灣履歷慣例、繁中） |
| `app/sources/base.py` | `JobSource` 介面（Protocol）＋ `JobPosting` 正規化；能力旗標 `searchable` / `url_only` |
| `app/sources/source_104.py` | 104 關鍵字搜尋（前端搜尋 JSON 端點，限頻、降級） |
| `app/sources/source_cake.py` | Cake 關鍵字搜尋 |
| `app/sources/source_yourator.py` | Yourator 關鍵字搜尋 |
| `app/sources/source_linkedin.py` | LinkedIn：貼網址抽取 + 產生搜尋深連結（不爬整頁） |
| `app/sources/source_url.py` | 通用「貼任意職缺網址」→ 抓單頁 → `JobPosting`（含上述各站 detail 解析） |
| `app/sources/registry.py` | 來源註冊表；`search_all(keywords, sources)` 聚合、`fetch_url(url)` 路由到對應解析器 |
| `app/agents/job_ranker.py` | `Profile` × `list[JobPosting]` → `list[JobMatch]` 依適配分數排序 top-N |
| `frontend/`（Vite + React + TS + Tailwind + shadcn/ui） | 產品級前端，建置成靜態檔由 FastAPI 提供 |

## 新資料模型（`app/models.py` 追加）

```python
class ResumeIssue(BaseModel):
    severity: str = Field(description="high | medium | low")
    area: str = Field(description="問題所在區塊，如『工作經歷』『技能』")
    problem: str
    fix: str = Field(description="具體可照做的修正建議")

class ResumeRewrite(BaseModel):
    original: str
    improved: str
    why: str

class ResumeAssessment(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    clarity_score: int = Field(ge=0, le=100, description="表達清晰度")
    impact_score: int = Field(ge=0, le=100, description="量化成果/影響力")
    ats_keyword_score: int = Field(ge=0, le=100, description="ATS 關鍵字涵蓋")
    localization_score: int = Field(ge=0, le=100, description="台灣履歷慣例符合度")
    completeness_score: int = Field(ge=0, le=100, description="完整度")
    summary: str = Field(description="一段總評")
    strengths: list[str] = Field(default_factory=list)
    issues: list[ResumeIssue] = Field(default_factory=list)
    rewrite_examples: list[ResumeRewrite] = Field(default_factory=list)

class JobPosting(BaseModel):
    source: str = Field(description="104 | cake | yourator | linkedin | url")
    title: str
    company: str
    location: str | None = None
    salary: str | None = None
    url: str
    snippet: str | None = Field(default=None, description="職缺摘要")
    requirements: list[str] = Field(default_factory=list)
    raw_text: str = Field(default="", description="原始職缺全文，供後續解析")

class JobMatch(BaseModel):
    job: JobPosting
    fit_score: int = Field(ge=0, le=100)
    matched: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    reason: str = Field(description="為什麼適合/不適合的一段說明")
```

`JobSource` 介面（`app/sources/base.py`）：

```python
class SearchResult(BaseModel):
    jobs: list[JobPosting] = Field(default_factory=list)
    blocked: bool = Field(default=False, description="被擋/查無資料時 True，前端據此提示")
    source: str

class JobSource(Protocol):
    name: str
    searchable: bool      # True 才支援關鍵字搜尋
    def search(self, keywords: str, limit: int = 20) -> SearchResult: ...
    def fetch(self, url: str) -> JobPosting | None: ...   # 不支援者回 None
```

## 產品級前端（Vite + React + TS + Tailwind + shadcn/ui）

- 為何不用 Next.js：此 app 是無 SSR 需求的 SPA，打 FastAPI 的 API。Vite 在 Windows 更輕、跑起來更省事，
  視覺與作品集價值一樣到位。建置成靜態檔由 FastAPI 在 `/` 提供（正式跑只需 `uvicorn`）；
  開發時用 `vite dev` + proxy 到 `:8000`。SSE 在兩種模式都可用。
- **三個畫面：**
  1. **履歷健檢**（M5）：上傳/貼履歷 → 健檢儀表板（總分環＋五項分數長條、優點卡、問題卡含嚴重度標籤、
     改寫前後對照）。非 JSON。
  2. **職缺探索**（M6）：關鍵字搜尋框（可選來源）＋推薦職缺卡片列表（職稱/公司/薪資/地點/適配%＋
     「為什麼適合」），LinkedIn 顯示為深連結；可貼任意網址加入單一職缺。
  3. **投遞包工作台**（M7）：左欄保留即時 agent 編排追蹤（v1 賣點）；右欄客製履歷/求職信/面試/公司情報
     渲染成正式文件；人工核可；**列印/匯出 PDF**（列印優化 CSS + `window.print()` 為 MVP）。

## 里程碑

依使用者決定「履歷優先」，順序為 M5 → M6 → M7。每個里程碑各自有可執行、可測的交付。

### M5（先做）：履歷上傳 + AI 健檢 + 產品級前端骨架
- `app/intake/resume_parser.py`：PDF/DOCX/文字 → 純文字（純文字解析含單元測試；PDF/DOCX 用小型 fixture）。
- `app/agents/resume_eval.py`：履歷文字 → `Profile` 結構化 + `ResumeAssessment`（mock LLM 測試）。
- `app/models.py`：追加 `ResumeIssue/ResumeRewrite/ResumeAssessment`。
- server：`POST /api/resume/evaluate`（multipart 上傳或貼文字）→ 串流「解析中→評估中→完成」並回 assessment。
- `frontend/`：Vite + React + Tailwind + shadcn 骨架；履歷健檢頁（上傳/貼 → 儀表板渲染）；
  FastAPI 提供建置產物。
- 相依：`pypdf`、`python-docx` 加入 requirements。
- **交付驗收**：使用者上傳一份履歷，看到非 JSON 的健檢儀表板（分數 + 優缺點 + 改寫建議）。

### M6：職缺探索（多來源搜尋 + 排序）
- `app/sources/`：`base`、`registry`、`source_104/cake/yourator`（searchable）、`source_linkedin`（url_only + 深連結）、`source_url`（通用）。各 source 限頻 + 降級 + 隔離；用錄製的 HTTP fixture 做離線測試。
- `app/agents/job_ranker.py`：`Profile` × jobs → 排序 `JobMatch`。
- server：`POST /api/jobs/search`（keywords + sources）、`POST /api/jobs/fetch`（url）。
- `frontend/`：職缺探索頁（搜尋框 + 來源勾選 + 排序卡片列表 + 貼網址）。
- **交付驗收**：輸入關鍵字 → 看到跨來源、依履歷排序的真實職缺卡片；貼網址可加入單一職缺。

### M7：投遞包工作台 + 正式文件渲染 + PDF
- `frontend/`：投遞包工作台頁，整合既有 `/api/run` + `/api/resume` SSE；左即時編排、右正式文件；
  人工核可；列印優化版面 + 匯出 PDF。
- 串接：從 M6 選定職缺 → 帶入既有投遞包流程（職缺文字即 `jd_text`，履歷即 `profile`）。
- **交付驗收**：選一則職缺 → 看 agent 即時工作 → 得到正式排版的客製履歷/求職信/面試包 → 核可 → 匯出 PDF。

## 測試策略

- 既有 55 passed / 1 deselected 全部維持綠。
- 新模組 TDD：parser（純文字、PDF/DOCX fixture）、resume_eval（mock LLM 結構化輸出）、
  各 source（離線 HTTP fixture，驗證解析與降級行為）、ranker（mock LLM）、server 新端點（TestClient）。
- 真實打外站的測試標記為 `live`（沿用既有 marker，預設略過）。
- 前端：先以 build 成功 + 關鍵渲染 smoke 為主（不過度投資 e2e）。

## 不做（YAGNI）

- 不做帳號/登入/多使用者、不做資料庫持久化（沿用 per-process MemorySaver；持久化留待真有需求）。
- 不做自動投遞（auto-apply）。
- 不做爬蟲反偵測（代理、CAPTCHA 破解、繞登入）。
- 不做行動 App。
```