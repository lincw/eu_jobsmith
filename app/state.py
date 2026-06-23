"""LangGraph 共享狀態。"""
from typing import TypedDict

from app.models import Profile, ParsedJob, MatchReport


class CopilotState(TypedDict):
    jd_text: str
    profile: Profile
    parsed_job: ParsedJob | None
    match_report: MatchReport | None
