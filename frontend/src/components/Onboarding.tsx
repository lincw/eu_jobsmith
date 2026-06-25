import { useEffect, useState } from "react"
import { Brand } from "../ui/Brand"
import { Button } from "../ui/Button"
import { Cpu, CheckCircle2, XCircle, Loader2, ArrowRight } from "../ui/icons"

interface BackendOption { id: string; label: string; available: boolean }

// 仿 Open Design 的開場：先讓使用者選本機 CLI（Claude Code / Codex CLI）並做連線測試，
// 確認可用再進入主畫面；之後仍可在右上角自由切換。
const CLI_IDS = ["claude_cli", "codex_cli"]

const DESC: Record<string, string> = {
  claude_cli: "用你的 Claude 訂閱（claude -p），免 API key、不吃額度。",
  codex_cli: "用你的 Codex 訂閱（codex exec），免 API key。",
}

export function Onboarding({ onDone }: { onDone: () => void }) {
  const [options, setOptions] = useState<BackendOption[]>([])
  const [selected, setSelected] = useState("")
  const [testing, setTesting] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null)
  const [starting, setStarting] = useState(false)

  useEffect(() => {
    fetch("/api/backend")
      .then((r) => r.json())
      .then((d: { options?: BackendOption[]; current?: string }) => {
        const opts = (d.options || []).filter((o) => CLI_IDS.includes(o.id))
        setOptions(opts)
        const firstAvail = opts.find((o) => o.available)
        setSelected(d.current && CLI_IDS.includes(d.current) ? d.current : (firstAvail?.id || opts[0]?.id || ""))
      })
      .catch(() => {})
  }, [])

  function choose(id: string) {
    setSelected(id); setResult(null)
  }

  async function test() {
    if (!selected) return
    setTesting(true); setResult(null)
    try {
      const r = await fetch("/api/backend/test", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ backend: selected }),
      })
      const d = await r.json()
      setResult({ ok: Boolean(d.ok), message: d.message || (d.ok ? "連線成功" : "連線失敗") })
    } catch {
      setResult({ ok: false, message: "連線發生問題，請確認伺服器是否啟動。" })
    } finally {
      setTesting(false)
    }
  }

  async function start() {
    if (!selected) return
    setStarting(true)
    try {
      await fetch("/api/backend", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ backend: selected }),
      })
      onDone()
    } finally {
      setStarting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm grid place-items-center p-4">
      <div className="w-full max-w-lg bg-white rounded-xl2 shadow-cardHover p-6 animate-fade-in-up">
        <div className="mb-5"><Brand /></div>
        <h1 className="text-lg font-bold text-slate-900 mb-1">先選擇你的 AI 後端</h1>
        <p className="text-sm text-slate-500 mb-4">
          本工具用你本機的 CLI 訂閱當 AI 引擎（免 API key）。選一個就能開始；想確認可先「測試連線」（非必須）。
          之後也能在右上角隨時切換，或改用 OpenAI 相容（BYOK）。
        </p>

        <div className="space-y-2.5">
          {options.map((o) => {
            const active = selected === o.id
            return (
              <button key={o.id} type="button" onClick={() => choose(o.id)}
                disabled={!o.available}
                aria-pressed={active}
                className={`w-full text-left rounded-xl border p-4 flex items-start gap-3 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-300 ${
                  active ? "border-brand-500 bg-brand-50/60 ring-1 ring-brand-200"
                    : "border-slate-200 hover:bg-slate-50"
                } ${o.available ? "" : "opacity-50 cursor-not-allowed"}`}>
                <span className={`grid place-items-center w-9 h-9 rounded-lg shrink-0 ${active ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-500"}`}>
                  <Cpu className="w-5 h-5" />
                </span>
                <span className="flex-1 min-w-0">
                  <span className="flex items-center gap-2">
                    <span className="font-medium text-slate-900">{o.label}</span>
                    {!o.available && <span className="text-xs text-slate-400">（未偵測到）</span>}
                  </span>
                  <span className="block text-sm text-slate-500 mt-0.5">{DESC[o.id] || ""}</span>
                </span>
              </button>
            )
          })}
        </div>

        {result && (
          <div className={`mt-4 text-sm rounded-lg p-3 flex items-center gap-2 ${
            result.ok ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"}`}>
            {result.ok ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <XCircle className="w-4 h-4 shrink-0" />}
            {result.message}
          </div>
        )}

        <div className="mt-5 flex items-center gap-3">
          <Button variant="secondary" onClick={test} loading={testing}
            disabled={!selected || starting}
            icon={testing ? undefined : Cpu}>
            {testing ? "測試中…" : "測試連線"}
          </Button>
          <Button onClick={start} loading={starting} disabled={!selected || testing} icon={ArrowRight}>
            開始使用
          </Button>
          <button type="button" onClick={onDone}
            className="ml-auto text-sm text-slate-400 hover:text-slate-600 rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-300">
            先略過
          </button>
        </div>
        {testing && (
          <p className="text-xs text-slate-400 mt-2 flex items-center gap-1">
            <Loader2 className="w-3 h-3 animate-spin" />首次呼叫 CLI 可能需要數秒，請稍候。
          </p>
        )}
      </div>
    </div>
  )
}
