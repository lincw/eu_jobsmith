import { useEffect, useState } from "react"

interface BackendOption { id: string; label: string; available: boolean }

// 讓使用者切換 LLM 後端（Claude Code CLI / Codex CLI 訂閱，仿 open-design）。
export function BackendSelector() {
  const [options, setOptions] = useState<BackendOption[]>([])
  const [current, setCurrent] = useState("")
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    fetch("/api/backend")
      .then((r) => r.json())
      .then((d) => { setOptions(d.options || []); setCurrent(d.current || "") })
      .catch(() => {})
  }, [])

  async function change(id: string) {
    setBusy(true)
    const prev = current
    setCurrent(id)
    try {
      const r = await fetch("/api/backend", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ backend: id }),
      })
      if (!r.ok) setCurrent(prev)
    } catch {
      setCurrent(prev)
    } finally {
      setBusy(false)
    }
  }

  if (!options.length) return null
  return (
    <label className="no-print flex items-center gap-2 text-xs text-slate-500">
      <span>引擎</span>
      <select
        value={current}
        disabled={busy}
        onChange={(e) => change(e.target.value)}
        className="border rounded-lg px-2 py-1 text-xs bg-white disabled:opacity-50"
      >
        {options.map((o) => (
          <option key={o.id} value={o.id} disabled={!o.available}>
            {o.label}{o.available ? "" : "（未偵測到）"}
          </option>
        ))}
      </select>
    </label>
  )
}
