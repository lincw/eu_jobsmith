from app.models import (
    ParsedJob, MatchReport, CompanyBrief, TailoredResume, CoverLetter, InterviewKit,
)
from app import graph as graph_mod


def _patch_all(monkeypatch, report: MatchReport):
    monkeypatch.setattr(graph_mod, "parse_job",
                        lambda jd_text: ParsedJob(title="AI 工程師", company="未來智能"))
    monkeypatch.setattr(graph_mod, "match_profile", lambda job, profile: report)
    monkeypatch.setattr(graph_mod, "research_company",
                        lambda name: CompanyBrief(company=name, funding="B 輪"))
    monkeypatch.setattr(graph_mod, "tailor_resume",
                        lambda job, profile: TailoredResume(summary="客製履歷"))
    monkeypatch.setattr(graph_mod, "write_cover_letter",
                        lambda job, profile, company: CoverLetter(body="求職信"))
    monkeypatch.setattr(graph_mod, "prepare_interview",
                        lambda job, profile, company: InterviewKit(technical_questions=["Q"]))


def _initial_state(profile):
    return {
        "jd_text": "（任意）", "profile": profile,
        "parsed_job": None, "match_report": None, "company_brief": None,
        "tailored_resume": None, "cover_letter": None, "interview_kit": None,
    }


def test_proceed_path_produces_all_outputs(monkeypatch, demo_profile):
    _patch_all(monkeypatch, MatchReport(score=82, recommend_proceed=True, reason="吻合"))
    final = graph_mod.build_graph().invoke(_initial_state(demo_profile))

    assert final["match_report"].score == 82
    assert final["company_brief"].funding == "B 輪"
    assert final["tailored_resume"].summary == "客製履歷"
    assert final["cover_letter"].body == "求職信"
    assert final["interview_kit"].technical_questions == ["Q"]


def test_stop_path_skips_fanout(monkeypatch, demo_profile):
    _patch_all(monkeypatch, MatchReport(score=40, recommend_proceed=False, reason="不符"))
    final = graph_mod.build_graph().invoke(_initial_state(demo_profile))

    assert final["match_report"].score == 40
    assert final["tailored_resume"] is None
    assert final["cover_letter"] is None
    assert final["interview_kit"] is None
    assert final["company_brief"] is None


def test_cover_and_interview_receive_company_brief(monkeypatch, demo_profile):
    seen = {}
    _patch_all(monkeypatch, MatchReport(score=80, recommend_proceed=True, reason="ok"))

    def cover(job, profile, company):
        seen["cover_company"] = company
        return CoverLetter(body="x")

    def interview(job, profile, company):
        seen["interview_company"] = company
        return InterviewKit()

    monkeypatch.setattr(graph_mod, "write_cover_letter", cover)
    monkeypatch.setattr(graph_mod, "prepare_interview", interview)

    graph_mod.build_graph().invoke(_initial_state(demo_profile))

    assert seen["cover_company"] is not None
    assert seen["cover_company"].funding == "B 輪"
    assert seen["interview_company"] is not None


def test_route_after_match_proceeds_returns_list():
    state = {"match_report": MatchReport(score=80, recommend_proceed=True, reason="高")}
    assert graph_mod.route_after_match(state) == ["resume_tailor", "company_research"]


def test_route_after_match_stops_low_score():
    state = {"match_report": MatchReport(score=50, recommend_proceed=True, reason="分數不足")}
    assert graph_mod.route_after_match(state) == "stop"


def test_route_after_match_stops_when_not_recommended():
    state = {"match_report": MatchReport(score=90, recommend_proceed=False, reason="不合")}
    assert graph_mod.route_after_match(state) == "stop"
