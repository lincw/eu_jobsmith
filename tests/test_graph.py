from langgraph.types import Command

from app.models import (
    ParsedJob, MatchReport, CompanyBrief, TailoredResume, CoverLetter,
    InterviewKit, CritiqueReport,
)
from app import graph as graph_mod

CONFIG = {"configurable": {"thread_id": "test-thread"}}


def _patch_base(monkeypatch, report: MatchReport):
    monkeypatch.setattr(graph_mod, "parse_job",
                        lambda jd_text: ParsedJob(title="AI 工程師", company="未來智能"))
    monkeypatch.setattr(graph_mod, "match_profile", lambda job, profile: report)
    monkeypatch.setattr(graph_mod, "research_company",
                        lambda name: CompanyBrief(company=name, funding="B 輪"))
    monkeypatch.setattr(graph_mod, "tailor_resume",
                        lambda job, profile, feedback=None: TailoredResume(summary="履歷"))
    monkeypatch.setattr(graph_mod, "write_cover_letter",
                        lambda job, profile, company, feedback=None: CoverLetter(body="信"))
    monkeypatch.setattr(graph_mod, "prepare_interview",
                        lambda job, profile, company, feedback=None: InterviewKit(technical_questions=["Q"]))


def _passing_critic(monkeypatch):
    monkeypatch.setattr(graph_mod, "critique_package",
                        lambda job, r, c, k: CritiqueReport(
                            resume_score=90, cover_letter_score=88, interview_score=85,
                            overall_pass=True, feedback=[]))


def _initial(profile):
    return {
        "jd_text": "（任意）", "profile": profile,
        "parsed_job": None, "match_report": None, "company_brief": None,
        "tailored_resume": None, "cover_letter": None, "interview_kit": None,
        "critique": None, "revision_count": 0, "approved": None,
    }


def test_proceed_runs_to_human_gate_then_resumes(monkeypatch, demo_profile):
    _patch_base(monkeypatch, MatchReport(score=82, recommend_proceed=True, reason="吻合"))
    _passing_critic(monkeypatch)
    g = graph_mod.build_graph()

    result = g.invoke(_initial(demo_profile), CONFIG)
    assert "__interrupt__" in result

    final = g.invoke(Command(resume="y"), CONFIG)
    assert final["approved"] is True
    assert final["tailored_resume"].summary == "履歷"
    assert final["company_brief"].funding == "B 輪"
    assert final["critique"].overall_pass is True


def test_stop_path_no_interrupt(monkeypatch, demo_profile):
    _patch_base(monkeypatch, MatchReport(score=40, recommend_proceed=False, reason="不符"))
    _passing_critic(monkeypatch)
    g = graph_mod.build_graph()

    result = g.invoke(_initial(demo_profile), CONFIG)
    assert "__interrupt__" not in result
    assert result["match_report"].score == 40
    assert result["tailored_resume"] is None


def test_failing_critic_loops_then_stops_at_max(monkeypatch, demo_profile):
    _patch_base(monkeypatch, MatchReport(score=82, recommend_proceed=True, reason="吻合"))
    calls = {"resume": 0, "critic": 0}

    def counting_resume(job, profile, feedback=None):
        calls["resume"] += 1
        return TailoredResume(summary=f"v{calls['resume']}")

    def always_fail(job, r, c, k):
        calls["critic"] += 1
        return CritiqueReport(resume_score=10, cover_letter_score=10, interview_score=10,
                              overall_pass=False, feedback=["再加強"])

    monkeypatch.setattr(graph_mod, "tailor_resume", counting_resume)
    monkeypatch.setattr(graph_mod, "critique_package", always_fail)
    g = graph_mod.build_graph()

    result = g.invoke(_initial(demo_profile), CONFIG)
    assert calls["critic"] == 2
    assert calls["resume"] == 2
    assert "__interrupt__" in result


def test_revise_passes_feedback_to_generators(monkeypatch, demo_profile):
    _patch_base(monkeypatch, MatchReport(score=82, recommend_proceed=True, reason="吻合"))
    seen = {"feedback": None}

    def resume_capture(job, profile, feedback=None):
        if feedback:
            seen["feedback"] = feedback
        return TailoredResume(summary="x")

    critic_calls = {"n": 0}

    def fail_once(job, r, c, k):
        critic_calls["n"] += 1
        if critic_calls["n"] == 1:
            return CritiqueReport(resume_score=10, cover_letter_score=10, interview_score=10,
                                  overall_pass=False, feedback=["把成果量化"])
        return CritiqueReport(resume_score=90, cover_letter_score=90, interview_score=90,
                              overall_pass=True, feedback=[])

    monkeypatch.setattr(graph_mod, "tailor_resume", resume_capture)
    monkeypatch.setattr(graph_mod, "critique_package", fail_once)
    g = graph_mod.build_graph()

    g.invoke(_initial(demo_profile), CONFIG)
    assert seen["feedback"] == ["把成果量化"]


def test_route_after_match():
    assert graph_mod.route_after_match(
        {"match_report": MatchReport(score=80, recommend_proceed=True, reason="高")}
    ) == "company_research"
    assert graph_mod.route_after_match(
        {"match_report": MatchReport(score=50, recommend_proceed=True, reason="低")}
    ) == "stop"


def test_route_after_critic():
    passing = {"critique": CritiqueReport(resume_score=90, cover_letter_score=90,
               interview_score=90, overall_pass=True), "revision_count": 1}
    assert graph_mod.route_after_critic(passing) == "approve"

    failing_under = {"critique": CritiqueReport(resume_score=10, cover_letter_score=10,
                     interview_score=10, overall_pass=False), "revision_count": 1}
    assert graph_mod.route_after_critic(failing_under) == "revise"

    failing_at_max = {"critique": CritiqueReport(resume_score=10, cover_letter_score=10,
                      interview_score=10, overall_pass=False), "revision_count": 2}
    assert graph_mod.route_after_critic(failing_at_max) == "approve"
