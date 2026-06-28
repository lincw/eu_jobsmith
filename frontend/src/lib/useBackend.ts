import { useEffect, useRef, useState } from "react"
import { newTaskId, stopTask } from "./taskControl"
import { useTranslation } from "react-i18next"

// 後端控制台共用資料層：右上角 popover 與「執行設定」面板都用這個 hook。
export interface BackendOption { id: string; label: string; available: boolean; kind: string; version?: string }
export interface CliModel { choices: string[]; current: string }
export interface ByokCfg { base_url: string; model: string; has_key: boolean }
export interface BackendData {
  current: string
  options: BackendOption[]
  cli_models: Record<string, CliModel>
  byok: ByokCfg
}
export type TestState = "loading" | { ok: boolean; msg: string } | undefined
export interface ByokForm { base_url: string; api_key: string; model: string }

function postJSON(url: string, body: unknown, signal?: AbortSignal) {
  return fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal })
}

export function useBackend(reloadKey = 0) {
  const { t } = useTranslation()
  const [data, setData] = useState<BackendData | null>(null)
  const [busy, setBusy] = useState(false)
  const [tests, setTests] = useState<Record<string, TestState>>({})
  const testTasksRef = useRef<Record<string, { taskId: string; ctrl: AbortController }>>({})

  async function reload(): Promise<BackendData | null> {
    try {
      const d: BackendData = await (await fetch("/api/backend")).json()
      setData(d)
      return d
    } catch { return null }
  }
  useEffect(() => {
    // 初次載入後端清單；reload 在 await 之後才 setState（非渲染期同步），是 effect 正當用途。
    // eslint-disable-next-line react-hooks/set-state-in-effect
    reload()
  }, [reloadKey])

  async function activate(id: string) {
    setBusy(true)
    try {
      const r = await postJSON("/api/backend", { backend: id })
      if (r.ok) setData((d) => (d ? { ...d, current: id } : d))
    } finally { setBusy(false) }
  }

  async function setModel(backend: string, model: string) {
    setData((d) => (d ? { ...d, cli_models: { ...d.cli_models, [backend]: { ...d.cli_models[backend], current: model } } } : d))
    await postJSON("/api/backend/model", { backend, model })
  }

  async function saveByok(cfg: ByokForm, activateAfter: boolean) {
    setBusy(true)
    try {
      await postJSON("/api/backend/byok", cfg)
      if (activateAfter) await activate("openai")
      await reload()
    } finally { setBusy(false) }
  }

  async function runTest(id: string) {
    const previous = testTasksRef.current[id]
    if (previous) {
      void stopTask(previous.taskId).catch(() => undefined)
      previous.ctrl.abort()
    }
    const ctrl = new AbortController()
    const taskId = newTaskId(`backend-${id}`)
    testTasksRef.current[id] = { taskId, ctrl }
    setTests((t) => ({ ...t, [id]: "loading" }))
    try {
      const d = await (await postJSON("/api/backend/test", { backend: id, task_id: taskId }, ctrl.signal)).json()
      setTests((tState) => ({ ...tState, [id]: { ok: Boolean(d.ok), msg: d.message || (d.ok ? t("backend.test_success") : t("backend.test_fail")) } }))
    } catch (e) {
      if ((e as Error)?.name === "AbortError") {
        setTests((tState) => ({ ...tState, [id]: { ok: false, msg: t("backend.test_stopped") } }))
        return
      }
      setTests((tState) => ({ ...tState, [id]: { ok: false, msg: t("backend.test_error") } }))
    } finally {
      if (testTasksRef.current[id]?.ctrl === ctrl) delete testTasksRef.current[id]
    }
  }

  async function stopTest(id: string) {
    const current = testTasksRef.current[id]
    if (!current) return
    try {
      await stopTask(current.taskId)
    } catch {
      // 停止失敗時仍中止前端等待。
    } finally {
      current.ctrl.abort()
      delete testTasksRef.current[id]
      setTests((tState) => ({ ...tState, [id]: { ok: false, msg: t("backend.test_stopped") } }))
    }
  }

  return { data, busy, tests, reload, activate, setModel, saveByok, runTest, stopTest }
}


export function modelLabel(m: string | undefined): string {
  return !m || m === "auto" ? "Default" : m
}
