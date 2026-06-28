import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"

export function ScoreBars({ scores }: { scores: Record<string, number> }) {
  const { t } = useTranslation()
  const LABELS: Record<string, string> = {
    clarity_score: t("score.clarity", "表達清晰度"),
    impact_score: t("score.impact", "量化成果"),
    ats_keyword_score: t("score.ats", "ATS 關鍵字"),
    localization_score: t("score.localization", "歐洲慣例"),
    completeness_score: t("score.completeness", "完整度"),
  }
  const [on, setOn] = useState(false)
  useEffect(() => {
    const timer = requestAnimationFrame(() => setOn(true))
    return () => cancelAnimationFrame(timer)
  }, [])
  return (
    <div className="space-y-3">
      {Object.entries(LABELS).map(([k, label]) => {
        const v = scores[k] ?? 0
        const color = v >= 80 ? "bg-emerald-500" : v >= 60 ? "bg-amber-500" : "bg-rose-500"
        return (
          <div key={k}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-slate-600">{label}</span>
              <span className="font-semibold text-slate-800">{v}</span>
            </div>
            <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
              <div
                className={`h-full ${color} rounded-full transition-[width] duration-700 ease-out`}
                style={{ width: on ? `${v}%` : 0 }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
