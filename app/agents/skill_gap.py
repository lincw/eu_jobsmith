"""技能缺口市場分析：純彙整搜到職缺的 requirements，比對履歷技能找出缺口。

無 LLM（便宜、可測）。比對採「子字串 + 字界」而非精確相等：
履歷寫「AI 工程師」時，職缺要求「AI」也應算已具備，不應誤列為缺口。
"""
from __future__ import annotations

import re
from collections import Counter

from app.models import Profile, JobPosting, SkillCount, SkillGapReport


def _norm(s: str) -> str:
    """小寫 + 收斂空白。"""
    return " ".join(str(s).lower().split())


def _is_short_ascii(s: str) -> bool:
    """純英數且很短（如 ai、ml、go、qa）——子字串比對易誤判，改用字界比對。"""
    return len(s) <= 3 and s.isascii() and s.replace("+", "").replace("#", "").isalnum()


def _covered(req: str, have: set[str]) -> bool:
    """這項職缺要求是否已被履歷技能涵蓋。

    - 完全相同；或
    - 某履歷技能是要求的子字串（履歷「python」⊂ 要求「python 後端」）；或
    - 要求是某履歷技能的子字串（要求「ai」⊂ 履歷「ai 工程師」）。
      短英數要求（ai/ml…）改用字界比對，避免「ai」誤中「rail/domain」。
    """
    for s in have:
        if req == s:
            return True
        if len(s) >= 2 and s in req:
            return True
        if len(req) >= 2:
            if _is_short_ascii(req):
                if re.search(rf"(?<![0-9a-z]){re.escape(req)}(?![0-9a-z])", s):
                    return True
            elif req in s:
                return True
    return False


def analyze_skill_gap(profile: Profile, jobs: list[JobPosting], top_n: int = 15) -> SkillGapReport:
    have_norms = {_norm(s) for s in (profile.skills or []) if s.strip()}
    counter: Counter[str] = Counter()
    display: dict[str, str] = {}
    for j in jobs:
        for req in (j.requirements or []):
            r = str(req).strip()
            if not r:
                continue
            key = _norm(r)
            if not key:
                continue
            counter[key] += 1
            display.setdefault(key, r)
    ranked = counter.most_common()
    top_demand = [SkillCount(skill=display[k], count=c) for k, c in ranked[:top_n]]
    your_gaps = [SkillCount(skill=display[k], count=c)
                 for k, c in ranked if not _covered(k, have_norms)][:top_n]
    have = [display[k] for k, _ in ranked if _covered(k, have_norms)]
    return SkillGapReport(top_demand=top_demand, your_gaps=your_gaps, have=have)
