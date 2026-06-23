import pytest
from pydantic import ValidationError

from app.models import Profile, ParsedJob, MatchReport


def test_profile_minimal_valid():
    p = Profile(name="小明", summary="後端工程師", raw_text="...")
    assert p.skills == []            # 預設空清單
    assert p.years_experience is None


def test_parsed_job_requires_title_and_company():
    with pytest.raises(ValidationError):
        ParsedJob(title="AI 工程師")  # 缺 company


def test_match_report_score_must_be_in_range():
    ok = MatchReport(score=80, recommend_proceed=True, reason="符合度高")
    assert ok.score == 80
    with pytest.raises(ValidationError):
        MatchReport(score=120, recommend_proceed=True, reason="超出範圍")
