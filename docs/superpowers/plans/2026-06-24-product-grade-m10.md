# M10 — 英雄級前端 + 設計系統 Implementation Plan

> **For agentic workers:** 由本 session 直接執行（沿用 M8/M9 的 inline + 對抗式審查模式）。視覺任務無法寫單元測試，閘門為 `npm run build`（tsc + vite）通過；後端任務用 pytest TDD。每個 Task 完成即 commit。

**Goal:** 把目前「能用但樸素」的前端，升級成有品牌、有設計系統、有英雄級多 agent 即時可視化、可貼 JD 網址自動抓取、產出可編輯並能匯出 .docx / PDF 的產品級體驗。

**Architecture:** 先建立設計 token + UI 原語（Card/Button/Badge/SectionCard）作為地基，所有後續畫面只消費原語以保證一致性。AgentTrace 重build 成「任務控制台」深色英雄面板（用 M9 telemetry 顯示每節點 token/$/延遲 + supervisor 節點 + 反思迴圈）。新增兩個後端端點：JD 網址抓取（104 走官方 job API、通用走 httpx+BeautifulSoup）、投遞包匯出（.docx 走 python-docx；PDF 走品牌化列印樣式）。

**Tech Stack:** React 19 + TS + Tailwind v3、lucide-react（圖示）、framer-motion（動效）、Google Fonts（Inter + Noto Sans TC）；後端 FastAPI + httpx + beautifulsoup4 + python-docx。

## Global Constraints

- 介面語言 Traditional Chinese（zh-Hant）；文案維持現有語氣。
- 單人本機、無登入；不得引入需登入/付費的雲服務。
- 後端仍以同步 `def` 串流端點（避免 claude_cli 同步 subprocess 阻塞事件迴圈）。
- 前端閘門：`cd frontend && npm run build` 必須成功（`tsc -b && vite build`）。`verbatimModuleSyntax` → 型別匯入一律 `import type`。
- 不得移除既有功能（自動找職缺、履歷健檢、投遞包工作台、後端切換、優雅降級、telemetry 顯示、人工核可）。
- 新後端依賴只可用純 Python / 已有預編譯 wheel 的套件（beautifulsoup4）；不得引入需系統庫的套件（weasyprint/GTK）。
- 圖示一律用 lucide-react，移除 emoji 作為功能性圖示（文案內的 emoji 可保留）。
- 設計 token 一律走 tailwind.config + CSS 變數；元件不得散落硬編色碼（既有可漸進替換）。

---

## File Structure

新增/修改：

- `frontend/index.html` — 字體、favicon、title、meta（修改）
- `frontend/tailwind.config.js` — 設計 token：brand 色階、字體、圓角、陰影、keyframes（修改）
- `frontend/src/index.css` — base layer、CSS 變數、品牌列印樣式（修改）
- `frontend/src/ui/` — UI 原語（新增）：`Card.tsx`、`Button.tsx`、`Badge.tsx`、`Brand.tsx`、`Skeleton.tsx`、`EmptyState.tsx`、`icons.ts`（lucide 重匯出）
- `frontend/src/App.tsx` — app shell：品牌頁首、segmented nav、背景（修改）
- `frontend/src/components/pipeline/AgentTrace.tsx` — 重build 成英雄任務控制台（修改）
- `frontend/src/components/pipeline/Documents.tsx` — 卡片改用原語 + 圖示 + 動效 + 可編輯（修改）
- `frontend/src/components/{Dashboard,ScoreRing,ScoreBars,IssueCard,RewriteCard}.tsx` — 健檢視覺升級（修改）
- `frontend/src/views/{JobSearchView,ResumeHealthView,PipelineView}.tsx` — 畫面升級、空狀態、JD 網址抓取、可編輯/匯出（修改）
- `frontend/src/types.ts` — 新增 telemetry 對映、可編輯封包、URL 抓取事件型別（修改）
- `app/intake/jd_fetch.py` — JD 網址抓取（新增）
- `app/export/docx_export.py` — 投遞包 → .docx（新增）
- `app/server.py` — `/api/jd/fetch`、`/api/export/docx` 端點（修改）
- `requirements.txt` — 加 `beautifulsoup4`（修改）
- `tests/test_jd_fetch.py`、`tests/test_docx_export.py` — 後端新功能測試（新增）

---

## Task 1: 設計系統地基（token + 字體 + base CSS + 依賴）

**Files:**
- Modify: `frontend/index.html`、`frontend/tailwind.config.js`、`frontend/src/index.css`、`frontend/package.json`
- Create: `frontend/src/ui/icons.ts`

**Interfaces — Produces（後續所有任務消費）:**
- Tailwind 色：`brand`（50–900 indigo→violet 品牌主色）、語意別名沿用 Tailwind（emerald/amber/rose/slate）。
- `fontFamily.sans = ['Inter','Noto Sans TC', system-ui...]`、`fontFamily.display` 同。
- `borderRadius.xl2 = '1rem'`、`boxShadow.card`、`boxShadow.cardHover`、`boxShadow.glow`。
- keyframes/animation：`pulse-node`、`fade-in-up`、`shimmer`、`dash`（SVG 連線流動）。
- CSS 變數於 `:root`（背景漸層、面板色）。
- `src/ui/icons.ts` 從 `lucide-react` 重匯出本專案會用到的圖示（單一進出口）。

**Steps:**

- [ ] 安裝依賴：`cd frontend && npm install lucide-react framer-motion`（記錄版本進 package.json）。
- [ ] `index.html`：`<html lang="zh-Hant">`；`<head>` 加 Google Fonts preconnect + Inter(400/500/600/700) + Noto Sans TC(400/500/700)；inline SVG favicon（品牌節點圖記，indigo→violet 漸層）；`<title>JobCopilot · 台灣 AI 求職 Co-pilot</title>`；meta description。
- [ ] `tailwind.config.js`：`theme.extend` 加入上述 brand 色階、fontFamily、borderRadius、boxShadow、keyframes、animation。
- [ ] `index.css`：`@layer base` 設 `body`（字體、抗鋸齒、文字色、背景漸層用 CSS 變數）、`h1–h3` display 字體、選取色、細捲軸；保留並擴充 `@media print`（品牌化：隱藏 `.no-print`、卡片去陰影、避免分頁切斷 `.avoid-break`）。
- [ ] `src/ui/icons.ts`：`export { Sparkles, Search, FileText, Mail, MessageSquare, Building2, ShieldCheck, CircleCheck, Loader2, Cpu, Coins, Timer, RefreshCw, Pencil, Download, Link as LinkIcon, ArrowLeft, Upload, FileDown, AlertTriangle, CheckCircle2, XCircle, ExternalLink } from 'lucide-react'`（依實際使用增補）。
- [ ] 驗證：`npm run build` 成功（此時畫面字體/背景已改變，但元件仍舊）。
- [ ] Commit：`feat(m10): T1 設計系統地基（brand token / 字體 / base CSS / 依賴）`

## Task 2: App shell + 品牌 + UI 原語

**Files:**
- Create: `frontend/src/ui/{Brand,Card,Button,Badge,Skeleton,EmptyState}.tsx`
- Modify: `frontend/src/App.tsx`、`frontend/src/components/BackendSelector.tsx`

**Interfaces — Produces:**
- `<Brand size?="sm"|"md" />` — logomark（SVG 節點圖記）+ wordmark「JobCopilot」+ 副標。
- `<Card className? interactive? as?>` — 白底、`rounded-xl2`、`shadow-card`、border；`interactive` 加 hover 抬升。
- `<Button variant="primary"|"secondary"|"ghost"|"danger" size? icon? loading? />`。
- `<Badge tone="brand"|"emerald"|"amber"|"rose"|"slate" />`（取代散落的 chip className）。
- `<Skeleton className />`（shimmer）、`<EmptyState icon title desc action? />`。

**Steps:**
- [ ] 建立 6 個原語元件，全部消費 T1 token；`Button` 用 lucide 圖示與 `Loader2`（loading 時旋轉）。
- [ ] `App.tsx`：頂部品牌頁首（`<Brand>` + 右側 `<BackendSelector>`）；nav 改為 segmented pill 控制（active 有 brand 底色 + 微動效）；背景用 base 漸層；保留三分頁「全掛載只切顯示」結構與 `pickJob`。
- [ ] `BackendSelector.tsx`：改用 `Cpu` 圖示 + 原語樣式（保留 `/api/backend` 邏輯）。
- [ ] 驗證：`npm run build` 成功。
- [ ] Commit：`feat(m10): T2 app shell + 品牌 + UI 原語`

## Task 3: 英雄級多 agent 即時任務控制台（重build AgentTrace）

**Files:**
- Modify: `frontend/src/components/pipeline/AgentTrace.tsx`、`frontend/src/views/PipelineView.tsx`、`frontend/src/types.ts`

**Interfaces:**
- Consumes：`done: string[]`、`running`、`revisions`、`status`、`telemetry: TelemetryEntry[]`（PipelineView 已有）、`nodeErrors`。
- 新增 props 由 PipelineView 傳入 `telemetry`、`nodeErrors`。

**設計：** 深色「mission control」面板（slate-900→slate-800 漸層、`shadow-glow`），把 8 agent + 2 supervisor 畫成**垂直編排時間軸**：
- 每個節點：狀態（pending=空心灰 / active=brand 脈動 `pulse-node` / done=emerald 勾 / error=amber 警示）、節點名 + 該節點 telemetry 徽章（`Cpu` tokens、`Coins` $、`Timer` ms，數值來自對映 `telemetry` 該 node 條目）。
- 節點間 SVG 連線；active→done 時連線以 `dash` 動效流動。
- 含 supervisor 節點（`supervisor_match`、`supervisor_critic`）顯示為菱形決策點。
- 頂部總計列：總 agent 數 / 總 LLM 呼叫 / 總 tokens / 總 $ / 總時長（沿用 PipelineView 既有 reduce，移進面板頂部）。
- 反思迴圈：`revisions > 1` 時在 critic↔生成節點間畫回圈箭頭 + 「第 N 輪」徽章。
- `framer-motion`：節點進場 `fade-in-up` stagger；active 脈動。

**Steps:**
- [ ] `types.ts`：確保 `TelemetryEntry` 有 `node`；新增 `AgentTraceProps` 所需型別（可內聯）。
- [ ] 重寫 `AgentTrace.tsx`：節點清單含 supervisor 節點；建 `node→telemetry` 映射；渲染時間軸 + 徽章 + 連線 + 反思迴圈 + 總計列；深色面板。
- [ ] `PipelineView.tsx`：把 telemetry 總計列移除（改由 AgentTrace 頂部呈現）；`<AgentTrace>` 增傳 `telemetry`、`nodeErrors`；面板改為非 `no-print`？（控制台僅螢幕用，維持 `no-print`）。
- [ ] 驗證：`npm run build` 成功。
- [ ] Commit：`feat(m10): T3 英雄級多 agent 即時任務控制台`

## Task 4: 投遞包文件卡升級（原語 + 圖示 + 動效）

**Files:**
- Modify: `frontend/src/components/pipeline/Documents.tsx`、`frontend/src/components/ScoreRing.tsx`

**Steps:**
- [ ] `Documents.tsx`：`Section` 改用 `<Card>` + 標題列 lucide 圖示（②`Search` 匹配、⑧`Building2` 公司、③`FileText` 履歷、④`Mail` 求職信、⑤`MessageSquare` 面試、⑥`ShieldCheck` 品管）；`Chips` 改用 `<Badge>`；卡片以 framer-motion `fade-in-up` 進場。
- [ ] `ScoreRing.tsx`：升級為漸層環、分數依高低變色（≥80 emerald / ≥60 amber / else rose）、數字動畫（可選）。
- [ ] 驗證：`npm run build` 成功。
- [ ] Commit：`feat(m10): T4 投遞包文件卡視覺升級`

## Task 5: 三大畫面升級 + 空狀態 + 骨架 + 行動裝置

**Files:**
- Modify: `frontend/src/views/{JobSearchView,ResumeHealthView,PipelineView}.tsx`、`frontend/src/components/{Dashboard,IssueCard,RewriteCard,ScoreBars}.tsx`

**Steps:**
- [ ] `JobSearchView`：輸入卡改原語；職缺卡升級（fit 分數環/徽章、來源 `<Badge>`、matched 標籤、hover 抬升）；busy 時顯示 `<Skeleton>` 職缺卡；`done && 0 jobs` 與初始用 `<EmptyState>`（圖示 + LinkedIn 後援 CTA）。
- [ ] `ResumeHealthView` + `Dashboard/IssueCard/RewriteCard/ScoreBars`：改原語 + 圖示；初始 `<EmptyState>`；評估中 `<Skeleton>`。
- [ ] `PipelineView`：輸入卡、核可列、降級提示、空狀態改原語 + 圖示；`grid lg:grid-cols-[300px_1fr]` 響應式（行動裝置控制台收合於上方）。
- [ ] App nav 與頁首行動裝置可用（`flex-wrap`、字級調整）。
- [ ] 驗證：`npm run build` 成功。
- [ ] Commit：`feat(m10): T5 三大畫面升級 + 空狀態 + 行動裝置`

## Task 6: 貼 JD 網址自動抓取

**Files:**
- Create: `app/intake/jd_fetch.py`、`tests/test_jd_fetch.py`
- Modify: `app/server.py`、`requirements.txt`、`frontend/src/views/PipelineView.tsx`、`frontend/src/types.ts`

**Interfaces — Produces:**
- `app/intake/jd_fetch.py`：
  - `fetch_jd(url: str) -> JDFetchResult`（`@dataclass JDFetchResult: title:str; company:str; text:str; source:str`）。
  - 104 job URL（regex `104\.com\.tw/job/(\w+)`）→ 打 `https://www.104.com.tw/job/ajax/content/{id}`（Referer `https://www.104.com.tw/job/{id}`）解析 JSON（jobName/custName/jobDetail/需求）。
  - 其他 URL → httpx GET（瀏覽器 UA、follow_redirects、timeout=20）→ BeautifulSoup 取 `<title>` + 主要文字（移除 script/style/nav/footer，collapse 空白）。
  - 抓取失敗 / 內容過短（<60 字）→ raise `JDFetchError`。
- `/api/jd/fetch`（POST `{url}`）→ `{title, company, text, source}` 或 400 友善訊息。

**Steps:**
- [ ] `requirements.txt` 加 `beautifulsoup4>=4.12`；`cd D:\Multi-Agent && .\.venv\Scripts\pip install beautifulsoup4`（PowerShell；外部腳本記得 `$env:PYTHONPATH="D:\Multi-Agent"`）。
- [ ] **先寫測試** `tests/test_jd_fetch.py`：
  - `test_extracts_104_via_api(monkeypatch)`：monkeypatch `jd_fetch._http_json` 回 104 假 JSON → 斷言 title/company/text 正確、source=="104"。
  - `test_extracts_generic_html(monkeypatch)`：monkeypatch httpx GET 回含雜訊的 HTML → 斷言抽出主文、移除 script。
  - `test_too_short_raises(monkeypatch)`：短內容 → `JDFetchError`。
- [ ] 跑測試確認 FAIL（模組未建）。
- [ ] 實作 `app/intake/jd_fetch.py`。
- [ ] 跑測試 PASS：`.\.venv\Scripts\python -m pytest tests/test_jd_fetch.py -q`。
- [ ] `server.py`：加 `/api/jd/fetch`（同步 `def`，try/except→400 友善訊息）。
- [ ] `PipelineView.tsx`：JD 輸入卡上方加「貼網址自動抓取」列（`LinkIcon` + URL input + `Button` 抓取）；成功填入 `jd`（並可選帶公司名）；失敗顯示提示。`types.ts` 加 `JDFetchResult`。
- [ ] 驗證：`npm run build` + 後端測試通過。
- [ ] Commit：`feat(m10): T6 貼 JD 網址自動抓取（104 API + 通用抽取）`

## Task 7: 可編輯產出 + .docx / PDF 匯出

**Files:**
- Create: `app/export/docx_export.py`、`tests/test_docx_export.py`
- Modify: `app/server.py`、`frontend/src/views/PipelineView.tsx`、`frontend/src/components/pipeline/Documents.tsx`、`frontend/src/types.ts`

**Interfaces — Produces:**
- `app/export/docx_export.py`：`build_docx(pkg: dict) -> bytes`（用 python-docx 寫入：標題=職缺/公司、客製履歷 summary+bullets、求職信 subject+body、面試重點；中文用預設字型即可，python-docx 不需註冊字型）。
- `/api/export/docx`（POST 投遞包 JSON）→ `StreamingResponse`/`Response`（`application/vnd.openxmlformats-officedocument.wordprocessingml.document`，`Content-Disposition: attachment; filename=...docx`）。
- 前端「可編輯封包」：PipelineView 維護 `edited` 狀態（複製自 `state`），文件卡進入「編輯模式」時改用 textarea 綁定 `edited`；匯出用 `edited ?? state`。

**Steps:**
- [ ] **先寫測試** `tests/test_docx_export.py`：
  - `test_build_docx_returns_valid_zip()`：`build_docx({...})` 回 bytes，開頭為 `PK`（docx=zip），長度>0。
  - `test_docx_contains_text()`：用 `python-docx.Document(BytesIO(bytes))` 讀回，斷言含履歷 summary 與求職信 body 文字。
- [ ] 跑測試 FAIL。
- [ ] 實作 `app/export/docx_export.py`。
- [ ] 跑測試 PASS：`.\.venv\Scripts\python -m pytest tests/test_docx_export.py -q`。
- [ ] `server.py`：加 `/api/export/docx`。
- [ ] 前端：
  - `Documents.tsx`：`ResumeDoc` / `CoverLetterDoc` 支援 `editable` + `onChange`（textarea）。
  - `PipelineView.tsx`：「編輯」切換鈕（`Pencil`）；維護 `edited` 封包；「下載 Word」鈕（`FileDown`，POST `/api/export/docx`，觸發下載）；「匯出 PDF」鈕沿用 `window.print()` 但改走品牌列印樣式（T1 已備）。
  - `types.ts`：加匯出封包型別。
- [ ] 驗證：`npm run build` + 後端測試通過。
- [ ] Commit：`feat(m10): T7 可編輯產出 + .docx 下載 + 品牌化 PDF 列印`

---

## 收尾（全 milestone）

- [ ] 全套後端測試：`.\.venv\Scripts\python -m pytest -q`（M8/M9 既有 + T6/T7 新增全綠）。
- [ ] `npm run build` 最終成功；`git status` 確認 dist 未被提交（.gitignore 已含）。
- [ ] 對抗式審查 workflow（多 agent / 多 lens：可用性、無障礙/對比、響應式、TS 型別、後端安全/錯誤處理）→ 修正 Critical/Important。
- [ ] 請使用者 `! D:\Multi-Agent\run.bat` 視覺驗收。

## Self-Review（計畫對規格）

- 視覺大改：T1–T5 涵蓋 token/字體/品牌/英雄可視化/卡片/畫面/空狀態/動效/圖示/行動裝置 ✓
- 使用者加選功能：T6 貼 JD 網址自動抓取 ✓、T7 可編輯產出 + .docx/PDF 匯出 ✓（歷史紀錄屬 M11）
- 不破壞既有：Global Constraints 明列保留清單 ✓
- 依賴風險：framer-motion/lucide-react（前端純 JS）、beautifulsoup4（純 Python）；不引入系統庫依賴 ✓
- 字型風險：PDF 走品牌列印（無需在伺服器註冊 CJK 字型）、docx 用 python-docx 預設字型（中文 OK）✓
