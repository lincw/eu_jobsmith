import { useEffect, useRef, useState } from "react"
import type { ChangeEvent } from "react"
import { useTranslation } from "react-i18next"
import type { ResumeAssessment, UserProfile, SSEEvent } from "../types"
import { readSSE } from "../sse"
import { newTaskId, stopTask } from "../lib/taskControl"
import { SAMPLE_RESUME } from "../sampleResume"
import { Dashboard } from "../components/Dashboard"
import { Card } from "../ui/Card"
import { Button } from "../ui/Button"
import { Skeleton } from "../ui/Skeleton"
import { EmptyState } from "../ui/EmptyState"
import { Gauge, Upload, Loader2, Timer, ListChecks, XCircle } from "../ui/icons"

const RESUME_HEALTH_WAIT_HINT = "Deep Check usually takes 30s to 2 mins. Long resumes or PDFs might take longer."
const DEEP_SAMPLE: ResumeAssessment = {
  assessment_mode: "deep",
  fallback_reason: "",
  overall_score: 86,
  clarity_score: 84,
  impact_score: 82,
  ats_keyword_score: 88,
  localization_score: 90,
  completeness_score: 86,
  summary: "這是一份Deep Check Complete時的範例。報告會同時檢查定位、成果量化、ATS Keywords、台灣Resume慣例與可直接套用的RewriteWay.",
  strengths: [
    "Clear target title, skills and experience support each other.",
    "Already partiallyImpact，可讓招募者快速判斷影響力。",
  ],
  issues: [
    {
      severity: "medium",
      area: "Impact",
      problem: "Some experience entries lack scale, improvement metrics, or user impact.",
      fix: "Rewrite 'Developed API' to 'Built payment API using FastAPI, reducing latency by 42% and supporting 120k users'.",
    },
    {
      severity: "low",
      area: "ATS Keywords",
      problem: "Keywords in skills and experience can be better aligned with the target job.",
      fix: "Add framework, database, cloud, testing, and deployment keywords based on the target title.",
    },
  ],
  rewrite_examples: [
    {
      original: "Responsible for backend API development and maintenance.",
      improved: "Built core API using FastAPI / PostgreSQL, reducing avg response time by 42% and supporting 120k daily requests.",
      why: "Added technology, results, and scale to help recruiters judge actual contribution.",
    },
  ],
}

function formatElapsed(seconds: number) {
  if (seconds < 60) return `${seconds}Second`
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return rest ? `${minutes}point${rest}Second` : `${minutes}point`
}

export function ResumeHealthView(
  { onProfile }: { onProfile?: (p: UserProfile, meta?: { label?: string; resumeLabel?: string }) => void },
) {
  const { t, i18n } = useTranslation();
  const [text, setText] = useState("")
  const [status, setStatus] = useState("")
  const [busy, setBusy] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [assessment, setAssessment] = useState<ResumeAssessment | null>(null)
  const [error, setError] = useState("")
  const abortRef = useRef<AbortController | null>(null)
  const taskIdRef = useRef("")
  const stoppingRef = useRef(false)

  useEffect(() => {
    if (!busy) return
    const id = window.setInterval(() => setElapsedSeconds((s) => s + 1), 1000)
    return () => window.clearInterval(id)
  }, [busy])

  async function evaluate(form: FormData, resumeLabel: string) {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    const taskId = newTaskId("resume-health")
    abortRef.current = ctrl
    taskIdRef.current = taskId
    stoppingRef.current = false
    form.append("task_id", taskId)
    setBusy(true); setError(""); setAssessment(null)
    setElapsedSeconds(0)
    setStatus(`${t("common.uploading", "上傳中…")}${t("resume_health.wait_hint", RESUME_HEALTH_WAIT_HINT)}`)
    try {
      const resp = await fetch("/api/resume/evaluate", { method: "POST", body: form, signal: ctrl.signal })
      await readSSE(resp, (ev: SSEEvent) => {
        if (ev.type === "progress") setStatus(ev.message)
        else if (ev.type === "profile") {
          onProfile?.(ev.data as UserProfile, { resumeLabel })  //This timesessionshared, acrosssession需手動儲存Profile
        }
        else if (ev.type === "assessment") setAssessment(ev.data as ResumeAssessment)
        else if (ev.type === "stopped") { stoppingRef.current = true; setStatus(ev.message || t("resume_health.stopped", "alreadyStop健檢")) }
        else if (ev.type === "error") setError(ev.message)
        else if (ev.type === "done") setStatus(t("common.done", "Finish"))
      })
    } catch (e) {
      if ((e as Error)?.name === "AbortError") return
      setError(t("common.connection_error", "連線發生問題，請確認伺服器是否啟動。"))
    } finally {
      if (abortRef.current === ctrl) {
        setBusy(false)
        abortRef.current = null
        taskIdRef.current = ""
        if (stoppingRef.current) setStatus(t("resume_health.stopped", "alreadyStop健檢"))
        stoppingRef.current = false
      }
    }
  }

  async function stopEvaluate() {
    stoppingRef.current = true
    setStatus(t("resume_health.stopping", "areStop健檢…"))
    try {
      await stopTask(taskIdRef.current)
    } catch {
      //even thoughStop請求失敗，仍中止目前前端串流，避免畫面卡住。    } finally {
      abortRef.current?.abort()
      setBusy(false)
      setStatus(t("resume_health.stopped", "alreadyStop健檢"))
    }
  }

  function onSubmitText() {
    if (!text.trim()) { setError(t("resume_health.error_no_text", "請先貼上或載入Resumecharacter")); return }
    const form = new FormData()
    form.append("resume_text", text)
    form.append("lang", i18n.language.startsWith("zh") ? "zh" : "en")
    evaluate(form, "貼上的Resume")
  }

  function onFile(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (!f) return
    const form = new FormData()
    form.append("file", f)
    form.append("lang", i18n.language.startsWith("zh") ? "zh" : "en")
    evaluate(form, f.name)
    e.target.value = ""
  }

  return (
    <div>
      <Card className="p-5 mb-6">
        <textarea
          className="w-full border border-slate-300 rounded-lg p-3 text-sm h-40 focus:outline-none focus:ring-2 focus:ring-brand-200"
          placeholder={t("resume_health.paste_placeholder", "貼上Resumecharacter…")}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="flex flex-wrap gap-2 mt-3 items-center">
          <Button onClick={onSubmitText} loading={busy} icon={Gauge}>{t("resume_health.start_check", "Start Check")}</Button>
          {busy && <Button variant="danger" onClick={stopEvaluate} icon={XCircle}>{t("common.stop", "Stop")}</Button>}
          <label className={`inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg font-medium border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 transition cursor-pointer focus-within:ring-2 focus-within:ring-brand-300 ${busy ? "opacity-50 pointer-events-none" : ""}`}>
            <Upload className="w-4 h-4" />{t("resume_health.upload_file", "Upload file (PDF/DOCX/TXT)")}
            <input type="file" accept=".pdf,.docx,.txt" className="sr-only" onChange={onFile} disabled={busy} />
          </label>
          {busy && (
            <span className="text-sm text-slate-500 inline-flex items-center gap-1.5">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>{status || t("common.preparing", "準備中…")}</span>
              <span className="text-slate-400">{t("common.waited", "Waited")} {formatElapsed(elapsedSeconds)}</span>
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
                  <h2 className="text-lg font-semibold text-slate-900">{t("resume_health.checking_title", "正在進行Resume健檢")}</h2>
                  <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-600">
                    <Timer className="h-3.5 w-3.5" />{t("common.waited", "Waited")} {formatElapsed(elapsedSeconds)}
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-600">{status || t("common.preparing", "準備中…")}</p>
                <p className="mt-1 text-sm text-slate-500">{t("resume_health.wait_hint", RESUME_HEALTH_WAIT_HINT)}</p>
              </div>
              <Button variant="danger" onClick={stopEvaluate} icon={XCircle}>{t("common.stop", "Stop")}</Button>
            </div>
            <div className="mt-5 grid gap-4 border-t border-slate-200 pt-4 md:grid-cols-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                  <ListChecks className="h-4 w-4 text-brand-600" />{t("resume_health.step_parse", "Parsing background")}
                </div>
                <p className="mt-1 text-xs text-slate-500">{t("resume_health.step_parse_desc", "Extracting name, title, skills and experience.")}</p>
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                  <Gauge className="h-4 w-4 text-brand-600" />{t("resume_health.step_score", "Deep評分")}
                </div>
                <p className="mt-1 text-xs text-slate-500">{t("resume_health.step_score_desc", "檢查ATS、Impact與台灣Resume慣例。")}</p>
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                  <Loader2 className="h-4 w-4 text-brand-600" />{t("resume_health.step_report", "Generating report")}
                </div>
                <p className="mt-1 text-xs text-slate-500">{t("resume_health.step_report_desc", "產出問題清單與Rewrite範例。")}</p>
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
            icon={Gauge}
            title={t("resume_health.empty_title", "貼上或上傳你的Resume，Start Check")}
            desc={t("resume_health.empty_desc", "AI會評分Clarity、Impact、ATS Keywords與Localization，並給出Areas for Improvement與Rewrite範例。")}
          />
        </Card>
      )}

      {assessment && <Dashboard a={assessment} />}
    </div>
  )
}
