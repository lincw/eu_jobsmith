"""技能缺口市場分析：純彙整搜到職缺的 requirements，比對履歷技能找出缺口。

無 LLM（便宜、可測）；以小寫正規化比對，保留原字串顯示。
"""
from __future__ import annotations

from collections import Counter

from app.models import Profile, JobPosting, SkillCount, SkillGapReport


def analyze_skill_gap(profile: Profile, jobs: list[JobPosting], top_n: int = 15) -> SkillGapReport:
    have_set = {s.strip().lower() for s in (profile.skills or []) if s.strip()}
    counter: Counter[str] = Counter()
    display: dict[str, str] = {}
    for j in jobs:
        for req in (j.requirements or []):
            r = str(req).strip()
            if not r:
                continue
            key = r.lower()
            counter[key] += 1
            display.setdefault(key, r)
    ranked = counter.most_common()
    top_demand = [SkillCount(skill=display[k], count=c) for k, c in ranked[:top_n]]
    your_gaps = [SkillCount(skill=display[k], count=c) for k, c in ranked if k not in have_set][:top_n]
    have = [display[k] for k, _ in ranked if k in have_set]
    return SkillGapReport(top_demand=top_demand, your_gaps=your_gaps, have=have)
