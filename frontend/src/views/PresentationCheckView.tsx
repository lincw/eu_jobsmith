import { useEffect, useRef, useState } from "react"
import type { ChangeEvent } from "react"
import { useTranslation } from "react-i18next"
import type { PresentationAssessment, SSEEvent, CandidateProfile } from "../types"
import { readSSE } from "../sse"
import { newTaskId, stopTask } from "../lib/taskControl"

import { Card } from "../ui/Card"
import { Button } from "../ui/Button"
import { Skeleton } from "../ui/Skeleton"
import { EmptyState } from "../ui/EmptyState"
import { MonitorPlay, Upload, Loader2, Timer, ListChecks, XCircle, X, UsersRound, Target, Briefcase } from "../ui/icons"



function formatElapsed(seconds: number) {
  if (seconds < 60) return `${seconds} 秒`
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return rest ? `${minutes} 分 ${rest} 秒` : `${minutes} 分`
}

export function PresentationCheckView({ activeProfile }: { activeProfile?: CandidateProfile | null }) {
  const { t } = useTranslation();
  const [text, setText] = useState("")
  const [jdText, setJdText] = useState("")
  const [label, setLabel] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [reportLang, setReportLang] = useState("zh-TW")
  const [status, setStatus] = useState("")
  const [busy, setBusy] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [assessment, setAssessment] = useState<PresentationAssessment | null>(null)
  const [error, setError] = useState("")
  const abortRef = useRef<AbortController | null>(null)
  const taskIdRef = useRef("")
  const stoppingRef = useRef(false)

  useEffect(() => {
    if (!busy) return
    const id = window.setInterval(() => setElapsedSeconds((s) => s + 1), 1000)
    return () => window.clearInterval(id)
  }, [busy])

  async function evaluate(form: FormData) {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    const taskId = newTaskId("presentation-check")
    abortRef.current = ctrl
    taskIdRef.current = taskId
    stoppingRef.current = false
    form.append("task_id", taskId)
    setBusy(true); setError(""); setAssessment(null)
    setElapsedSeconds(0)
    setStatus(`${t("common.uploading", "上傳中…")}${t("presentation.wait_hint", "分析簡報通常需要 1 到 2 分鐘，請耐心等候。")}`)
    try {
      const resp = await fetch("/api/presentation/evaluate", { method: "POST", body: form, signal: ctrl.signal })
      await readSSE(resp, (ev: SSEEvent) => {
        if (ev.type === "progress") setStatus(ev.message)
        else if (ev.type === "assessment") setAssessment(ev.data as PresentationAssessment)
        else if (ev.type === "stopped") { stoppingRef.current = true; setStatus(ev.message || t("presentation.stopped", "已停止分析")) }
        else if (ev.type === "error") setError(ev.message)
        else if (ev.type === "done") setStatus(t("common.done", "完成"))
      })
    } catch (e) {
      if ((e as Error)?.name === "AbortError") return
      setError(t("common.connection_error", "連線發生問題，請確認伺服器是否啟動。"))
    } finally {
      if (abortRef.current === ctrl) {
        setBusy(false)
        abortRef.current = null
        taskIdRef.current = ""
        if (stoppingRef.current) setStatus(t("presentation.stopped", "已停止分析"))
        stoppingRef.current = false
      }
    }
  }

  async function stopEvaluate() {
    stoppingRef.current = true
    setStatus(t("presentation.stopping", "正在停止分析…"))
    try {
      await stopTask(taskIdRef.current)
    } catch {
      // ignore
    } finally {
      abortRef.current?.abort()
      setBusy(false)
      setStatus(t("presentation.stopped", "已停止分析"))
    }
  }

  function onSubmitAction() {
    if (!file && !text.trim()) { setError(t("presentation.error_no_text", "請先貼上或載入簡報文字")); return }
    const form = new FormData()
    if (file) {
      form.append("file", file)
    } else {
      form.append("presentation_text", text)
    }
    if (jdText.trim()) {
      form.append("jd", jdText)
    }
    if (activeProfile?.profile) {
      form.append("profile_json", JSON.stringify(activeProfile.profile))
    }
    form.append("report_lang", reportLang)
    if (label.trim()) form.append("label", label.trim())
    evaluate(form)
  }

  function onFile(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (f) setFile(f)
    e.target.value = ""
  }

  const hrQuestions = assessment?.questions?.filter((q) => q.role === "hr") || []
  const leaderQuestions = assessment?.questions?.filter((q) => q.role === "leader") || []
  const ceoQuestions = assessment?.questions?.filter((q) => q.role === "ceo") || []

  return (
    <div>
      <Card className="p-5 mb-6">
        <textarea
          className="w-full border border-slate-300 rounded-lg p-3 text-sm h-40 focus:outline-none focus:ring-2 focus:ring-brand-200 disabled:bg-slate-50"
          placeholder={t("presentation.paste_placeholder", "貼上簡報文字…")}
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={!!file || busy}
        />
        {file && (
          <div className="mt-2 inline-flex items-center gap-2 bg-brand-50 text-brand-700 rounded-lg px-3 py-1.5 text-sm">
            <Upload className="w-3.5 h-3.5" />{t("search_file_selected", "已選取：")}{file.name}
            <button type="button" onClick={() => setFile(null)} aria-label={t("presentation.remove_file", "移除已選檔案")} disabled={busy}
              className="rounded hover:bg-brand-100 p-0.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-300">
              <X className="w-3 h-3" />
            </button>
          </div>
        )}
        <div className="mt-2 flex items-center">
          <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer select-none">
            <input type="checkbox" className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
              checked={reportLang === "en"} onChange={(e) => setReportLang(e.target.checked ? "en" : "zh-TW")} disabled={busy} />
            {t("presentation.generate_english", "用英文產出提問 (Generate English Questions)")}
          </label>
        </div>
        <div className="mt-3">
          <textarea
            className="w-full border border-slate-300 rounded-lg p-3 text-sm h-24 focus:outline-none focus:ring-2 focus:ring-brand-200 disabled:bg-slate-50"
            placeholder={t("presentation.paste_jd", "貼上職缺描述 (JD)，這能讓 AI 提出的問題更精準（選填）…")}
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
            disabled={busy}
          />
        </div>
        {activeProfile && (
          <div className="mt-1 text-sm text-slate-500">
            💡 {t("presentation.auto_attach_profile", "將自動附上目前載入的履歷：")}<span className="font-medium text-slate-700">{activeProfile.label}</span>
          </div>
        )}
        <div className="mt-3 flex items-center gap-2">
          <input 
            type="text" 
            placeholder={t("presentation.label_placeholder", "設定簡報名稱（選填）")}
            value={label} 
            onChange={(e) => setLabel(e.target.value)}
            disabled={busy}
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-brand-200 disabled:bg-slate-50"
          />
        </div>
        <div className="flex flex-wrap gap-2 mt-3 items-center">
          <Button onClick={onSubmitAction} loading={busy} icon={MonitorPlay}>{t("presentation.start_evaluate", "開始分析")}</Button>
          {busy && <Button variant="danger" onClick={stopEvaluate} icon={XCircle}>{t("common.stop", "停止")}</Button>}
          <label className={`inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg font-medium border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 transition cursor-pointer focus-within:ring-2 focus-within:ring-brand-300 ${busy ? "opacity-50 pointer-events-none" : ""}`}>
            <Upload className="w-4 h-4" />{t("presentation.upload_file", "上傳簡報（PDF）")}
            <input type="file" accept=".pdf,.txt" className="sr-only" onChange={onFile} disabled={busy} />
          </label>
          {busy && (
            <span className="text-sm text-slate-500 inline-flex items-center gap-1.5">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>{status || t("common.preparing", "準備中…")}</span>
              <span className="text-slate-400">{t("common.waited", "已等待")} {formatElapsed(elapsedSeconds)}</span>
            </span>
          )}
        </div>
        {error && <p className="text-sm text-rose-600 mt-2">{error}</p>}
      </Card>

      {busy && !assessment && (
        <div className="space-y-6">
          <Card className="p-6">
            <div className="flex flex-col gap-5 sm:flex-row sm:items-start">
              <div className="h-12 w-12 shrink-0 rounded-lg bg-brand-50 text-brand-700 grid place-items-center">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-lg font-semibold text-slate-900">{t("presentation.evaluating_title", "正在進行簡報分析")}</h2>
                  <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-600">
                    <Timer className="h-3.5 w-3.5" />{t("common.waited", "已等待")} {formatElapsed(elapsedSeconds)}
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-600">{status || t("common.preparing", "準備中…")}</p>
                <p className="mt-1 text-sm text-slate-500">{t("presentation.wait_hint", "分析簡報通常需要 1 到 2 分鐘，請耐心等候。")}</p>
              </div>
              <Button variant="danger" onClick={stopEvaluate} icon={XCircle}>{t("common.stop", "停止")}</Button>
            </div>
            <div className="mt-5 grid gap-4 border-t border-slate-200 pt-4 md:grid-cols-2">
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                  <ListChecks className="h-4 w-4 text-brand-600" />{t("presentation.step_parse", "解析內容")}
                </div>
                <p className="mt-1 text-xs text-slate-500">{t("presentation.step_parse_desc", "讀取 PDF 與文字內容。")}</p>
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                  <MonitorPlay className="h-4 w-4 text-brand-600" />{t("presentation.step_evaluate", "深度評估")}
                </div>
                <p className="mt-1 text-xs text-slate-500">{t("presentation.step_evaluate_desc", "以 HR 和 Group Leader 角度產生面試題。")}</p>
              </div>
            </div>
            <div className="mt-5 space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-4/5" />
            </div>
          </Card>
        </div>
      )}

      {!busy && !assessment && !error && (
        <Card className="p-2">
          <EmptyState
            icon={MonitorPlay}
            title={t("presentation.empty_title", "上傳你的簡報，預測面試問題")}
            desc={t("presentation.empty_desc", "AI 將扮演 HR 和 Group Leader 兩個角色，根據你簡報的內容進行分析，並針對可能的問題點進行提問預測。")}
          />
        </Card>
      )}

      {assessment && (
        <div className="space-y-6">
          <Card className="p-6">
            <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
              <MonitorPlay className="w-5 h-5 text-brand-600" /> {t("presentation.summary_title", "簡報分析總結")}
            </h2>
            <p className="text-slate-700 whitespace-pre-wrap">{assessment.summary}</p>
          </Card>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="p-6">
              <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
                <UsersRound className="w-5 h-5 text-rose-500" /> {t("presentation.hr_questions", "HR 可能的提問")}
              </h2>
              {hrQuestions.length === 0 ? (
                <p className="text-sm text-slate-500">{t("presentation.no_hr_questions", "沒有 HR 相關提問")}</p>
              ) : (
                <ul className="space-y-4">
                  {hrQuestions.map((q, idx) => (
                    <li key={idx} className="bg-rose-50 rounded-lg p-4 border border-rose-100">
                      <p className="font-semibold text-rose-900 mb-2">{q.question}</p>
                      <p className="text-sm text-rose-700"><span className="font-medium">{t("presentation.reason", "考量點：")}</span>{q.reason}</p>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card className="p-6">
              <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
                <Target className="w-5 h-5 text-blue-500" /> {t("presentation.leader_questions", "Group Leader 可能的提問")}
              </h2>
              {leaderQuestions.length === 0 ? (
                <p className="text-sm text-slate-500">{t("presentation.no_leader_questions", "沒有 Group Leader 相關提問")}</p>
              ) : (
                <ul className="space-y-4">
                  {leaderQuestions.map((q, idx) => (
                    <li key={idx} className="bg-blue-50 rounded-lg p-4 border border-blue-100">
                      <p className="font-semibold text-blue-900 mb-2">{q.question}</p>
                      <p className="text-sm text-blue-700"><span className="font-medium">{t("presentation.reason", "考量點：")}</span>{q.reason}</p>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card className="p-6 md:col-span-2">
              <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-purple-500" /> {t("presentation.ceo_questions", "CEO 可能的提問")}
              </h2>
              {ceoQuestions.length === 0 ? (
                <p className="text-sm text-slate-500">{t("presentation.no_ceo_questions", "沒有 CEO 相關提問")}</p>
              ) : (
                <ul className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {ceoQuestions.map((q, idx) => (
                    <li key={idx} className="bg-purple-50 rounded-lg p-4 border border-purple-100">
                      <p className="font-semibold text-purple-900 mb-2">{q.question}</p>
                      <p className="text-sm text-purple-700"><span className="font-medium">{t("presentation.reason", "考量點：")}</span>{q.reason}</p>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
