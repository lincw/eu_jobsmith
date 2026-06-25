import { useEffect, useState } from "react"
import { Cpu, ChevronDown, RefreshCw, CheckCircle2, XCircle, Loader2, KeyRound, CircleDot, Circle } from "../ui/icons"

interface BackendOption { id: string; label: string; available: boolean; kind: string }
interface CliModel { choices: string[]; current: string }
interface ByokCfg { base_url: string; model: string; has_key: boolean }
interface BackendData {
  current: string
  options: BackendOption[]
  cli_models: Record<string, CliModel>
  byok: ByokCfg
}
type TestState = "loading" | { ok: boolean; msg: string } | undefined

// 右上角 AI 後端控制台（仿 open-design）：本機 CLI（掃描／測試／選模型）＋ BYOK（OpenAI 相容）。
// 選了即生效，測試只是檢查連線、非門檻。anthropic 是有效後端但不在此露出。
export function BackendSelector() {
  const [data, setData] = useState<BackendData | null>(null)
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [tests, setTests] = useState<Record<string, TestState>>({})
  const [byok, setByok] = useState({ base_url: "", api_key: "", model: "" })

  async function load() {
    try {
      const d: BackendData = await (await fetch("/api/backend")).json()
      setData(d)
      setByok({ base_url: d.byok.base_url || "", api_key: "", model: d.byok.model || "" })
    } catch { /* 後端未啟動則不顯示 */ }
  }
  useEffect(() => {
    // load() 在 await fetch 之後才 setState（非渲染期同步設值）；初次載入後端清單是 effect 正當用途。
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load()
  }, [])

  async function activate(id: string) {
    setBusy(true)
    try {
      const r = await fetch("/api/backend", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ backend: id }),
      })
      if (r.ok) setData((d) => (d ? { ...d, current: id } : d))
    } finally { setBusy(false) }
  }

  async function setModel(backend: string, model: string) {
    setData((d) => (d ? { ...d, cli_models: { ...d.cli_models, [backend]: { ...d.cli_models[backend], current: model } } } : d))
    await fetch("/api/backend/model", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ backend, model }),
    })
  }

  async function runTest(id: string) {
    setTests((t) => ({ ...t, [id]: "loading" }))
    try {
      const d = await (await fetch("/api/backend/test", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ backend: id }),
      })).json()
      setTests((t) => ({ ...t, [id]: { ok: Boolean(d.ok), msg: d.message || (d.ok ? "連線成功" : "連線失敗") } }))
    } catch {
      setTests((t) => ({ ...t, [id]: { ok: false, msg: "連線發生問題，請確認伺服器已啟動。" } }))
    }
  }

  async function saveByok(activate_after: boolean) {
    setBusy(true)
    try {
      await fetch("/api/backend/byok", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(byok),
      })
      if (activate_after) await activate("openai")
      await load()
    } finally { setBusy(false) }
  }

  async function testByok() {
    await saveByok(false)   // 先存目前表單，再用存好的設定測試
    await runTest("openai")
  }

  if (!data) return null
  const currentLabel = data.options.find((o) => o.id === data.current)?.label || data.current
  const shown = data.options.filter((o) => o.kind === "cli" || o.kind === "byok")

  return (
    <div className="relative no-print">
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open}
        title="切換 AI 後端：本機 CLI 訂閱或 OpenAI 相容（BYOK）。"
        className={`inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white pl-3 pr-2 py-1.5 text-xs text-slate-700 shadow-card hover:bg-slate-50 ${busy ? "opacity-60" : ""}`}>
        <Cpu className="w-4 h-4 text-brand-500" />
        <span className="font-medium text-slate-800">{currentLabel}</span>
        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} aria-hidden />
          <div className="absolute right-0 mt-2 w-[23rem] max-w-[calc(100vw-2rem)] z-50 rounded-xl border border-slate-200 bg-white shadow-cardHover p-3 animate-fade-in-up">
            <div className="flex items-center justify-between mb-2 px-1">
              <span className="text-sm font-semibold text-slate-800">AI 後端</span>
              <button type="button" onClick={load} disabled={busy}
                className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-brand-600 rounded px-1.5 py-1 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-300 disabled:opacity-50">
                <RefreshCw className={`w-3.5 h-3.5 ${busy ? "animate-spin" : ""}`} />重新掃描
              </button>
            </div>

            <div className="space-y-2">
              {shown.map((o) => {
                const active = o.id === data.current
                const t = tests[o.id]
                return (
                  <div key={o.id}
                    className={`rounded-lg border p-3 transition ${active ? "border-brand-400 bg-brand-50/50" : "border-slate-200"}`}>
                    <div className="flex items-center gap-2">
                      <button type="button" onClick={() => activate(o.id)} disabled={busy}
                        className="flex items-center gap-2 flex-1 min-w-0 text-left rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-300 disabled:opacity-60">
                        {active ? <CircleDot className="w-4 h-4 text-brand-600 shrink-0" /> : <Circle className="w-4 h-4 text-slate-300 shrink-0" />}
                        {o.kind === "byok" ? <KeyRound className="w-4 h-4 text-slate-400 shrink-0" /> : <Cpu className="w-4 h-4 text-slate-400 shrink-0" />}
                        <span className="font-medium text-sm text-slate-800 truncate">{o.label}</span>
                      </button>
                      {o.kind === "cli" && (
                        <span className={`text-xs shrink-0 ${o.available ? "text-emerald-600" : "text-slate-400"}`}>
                          {o.available ? "已偵測" : "未偵測"}
                        </span>
                      )}
                    </div>

                    {o.kind === "cli" && (
                      <div className="mt-2 flex items-center gap-2">
                        <label className="sr-only" htmlFor={`model-${o.id}`}>{o.label} 模型</label>
                        <select id={`model-${o.id}`} value={data.cli_models[o.id]?.current || "auto"}
                          onChange={(e) => setModel(o.id, e.target.value)} disabled={busy}
                          className="flex-1 min-w-0 border border-slate-300 rounded-lg px-2 py-1 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-brand-200 disabled:opacity-50">
                          {(data.cli_models[o.id]?.choices || []).map((c) => (
                            <option key={c} value={c}>{c === "auto" ? "自動分層（推薦）" : c}</option>
                          ))}
                        </select>
                        <button type="button" onClick={() => runTest(o.id)} disabled={busy || t === "loading"}
                          className="text-xs border border-slate-300 rounded-lg px-2.5 py-1 text-slate-600 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-300 disabled:opacity-50">
                          測試
                        </button>
                      </div>
                    )}

                    {o.kind === "byok" && (
                      <div className="mt-2 space-y-1.5">
                        <input value={byok.base_url} onChange={(e) => setByok((b) => ({ ...b, base_url: e.target.value }))}
                          placeholder="Base URL（例：https://api.deepseek.com/v1）" aria-label="Base URL"
                          className="w-full border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-brand-200" />
                        <input value={byok.api_key} onChange={(e) => setByok((b) => ({ ...b, api_key: e.target.value }))}
                          type="password" autoComplete="off"
                          placeholder={data.byok.has_key ? "API Key（已設定，留空＝不變更）" : "API Key"} aria-label="API Key"
                          className="w-full border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-brand-200" />
                        <input value={byok.model} onChange={(e) => setByok((b) => ({ ...b, model: e.target.value }))}
                          placeholder="Model（例：deepseek-chat / gpt-4o-mini）" aria-label="Model"
                          className="w-full border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-brand-200" />
                        <div className="flex items-center gap-2 pt-0.5">
                          <button type="button" onClick={testByok} disabled={busy || t === "loading"}
                            className="text-xs border border-slate-300 rounded-lg px-2.5 py-1 text-slate-600 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-300 disabled:opacity-50">
                            測試
                          </button>
                          <button type="button" onClick={() => saveByok(true)} disabled={busy}
                            className="text-xs bg-brand-600 text-white rounded-lg px-2.5 py-1 hover:bg-brand-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-300 disabled:opacity-50">
                            儲存並啟用
                          </button>
                        </div>
                      </div>
                    )}

                    {t && (
                      <div className={`mt-2 text-xs inline-flex items-center gap-1 ${
                        t === "loading" ? "text-slate-500" : t.ok ? "text-emerald-600" : "text-rose-600"}`}>
                        {t === "loading" ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          : t.ok ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                        {t === "loading" ? "測試中…" : t.msg}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            <p className="text-xs text-slate-400 mt-2 px-1">
              選了即生效；測試只是檢查連線、非必須。BYOK 金鑰只寫進你本機的 .env，不會外傳。
            </p>
          </div>
        </>
      )}
    </div>
  )
}
