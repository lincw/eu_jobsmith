from app.agents import resume_eval as mod
from app.models import Profile, ResumeAssessment, ResumeIssue
from tests.conftest import FakeLLM


def test_structure_profile_returns_profile(monkeypatch):
    canned = Profile(name="王小明", summary="後端工程師", skills=["Python"], raw_text="原文")
    monkeypatch.setattr(mod, "get_llm", lambda tier, **kw: FakeLLM(canned))
    result = mod.structure_profile("（履歷全文）")
    assert isinstance(result, Profile)
    assert result.name == "王小明"


def test_structure_profile_uses_standard_tier(monkeypatch):
    # 履歷解析改用 sonnet（standard）：是後續匹配/排序/技能缺口的共同上游，要抽得準。
    seen = {}
    canned = Profile(name="x", summary="y", raw_text="z")

    def fake(tier, **kw):
        seen["tier"] = tier
        seen["kw"] = kw
        return FakeLLM(canned)

    monkeypatch.setattr(mod, "get_llm", fake)
    mod.structure_profile("text")
    assert seen["tier"] == "standard"
    assert seen["kw"]["timeout"] == 60
    assert seen["kw"]["structured_retries"] == 1


def test_structure_profile_fills_raw_text_when_empty(monkeypatch):
    canned = Profile(name="王", summary="s", raw_text="")
    monkeypatch.setattr(mod, "get_llm", lambda tier, **kw: FakeLLM(canned))
    result = mod.structure_profile("完整履歷文字")
    assert result.raw_text == "完整履歷文字"


def test_structure_profile_fills_required_fields_when_llm_omits_them(monkeypatch):
    canned = Profile(name="", summary="", skills=[], raw_text="")
    monkeypatch.setattr(mod, "get_llm", lambda tier, **kw: FakeLLM(canned))
    result = mod.structure_profile(
        "Alex Chen\nFull Stack Engineer\nPython FastAPI React PostgreSQL\n"
        "Built internal APIs and reduced processing time by 30%."
    )

    assert result.name
    assert result.summary
    assert result.skills
    assert result.raw_text


def test_structure_profile_replaces_name_not_present_in_resume(monkeypatch):
    canned = Profile(name="狀在中", summary="AI 工程師", skills=["Python"], raw_text="")
    monkeypatch.setattr(mod, "get_llm", lambda tier, **kw: FakeLLM(canned))

    result = mod.structure_profile("王予\nAI Engineer\nPython FastAPI React")

    assert result.name == "王予"


def test_structure_profile_ignores_pdf_status_fragment_before_name(monkeypatch):
    canned = Profile(name="狀在中", summary="AI 工程師", skills=["Python"], raw_text="")
    monkeypatch.setattr(mod, "get_llm", lambda tier, **kw: FakeLLM(canned))
    resume_text = "\n".join([
        "個男   25     (2024/8)",
        "狀在中",
        "主⼿0979-352-452",
        "E-mail eugenew0226@gmail.com",
        "址中正路 ***",
        "⼤",
        "理⼤",
        "2018/9~2023/6",
        "⼯作",
        "年2~3 年⼯作",
        "⼯師",
        "和潤司（其輔助  500 以上）",
        "⼯師|內",
        "2024/9~ 在",
        " 開⼯師",
        "光壽",
        "⼯師",
        "2023/1~2024/41 年 4 個⽉",
        "件",
        "希性⼯作",
        "上⽇",
        "可上⽇取可上",
        "希⾯",
        "希",
        "希⼯師  ⼯師",
        "王予",
        "和潤司|⼯師",
    ])

    result = mod.structure_profile(resume_text)

    assert result.name == "王予"


def test_structure_profile_falls_back_when_llm_parse_fails(monkeypatch):
    def fail(_tier):
        raise RuntimeError("Claude Code CLI 回覆不是合法 JSON")

    monkeypatch.setattr(mod, "get_llm", fail)
    result = mod.structure_profile(
        "Full Stack Engineer\nTypeScript React Node.js AWS\n"
        "Developed dashboard and REST API for business users."
    )

    assert result.name
    assert result.summary
    assert result.skills
    assert result.raw_text


def test_evaluate_resume_returns_assessment(monkeypatch):
    canned = ResumeAssessment(
        overall_score=78, clarity_score=80, impact_score=70,
        ats_keyword_score=75, localization_score=85, completeness_score=80,
        summary="整體不錯", strengths=["技能清楚"],
        issues=[ResumeIssue(severity="medium", area="工作經歷", problem="缺量化", fix="加數字")],
    )
    monkeypatch.setattr(mod, "get_llm", lambda tier, **kw: FakeLLM(canned))
    result = mod.evaluate_resume("履歷全文", Profile(name="王", summary="s", raw_text="r"))
    assert isinstance(result, ResumeAssessment)
    assert result.overall_score == 78
    assert result.issues[0].severity == "medium"


def test_evaluate_resume_uses_deep_tier_with_larger_max_tokens(monkeypatch):
    seen = {}
    canned = ResumeAssessment(
        overall_score=1, clarity_score=1, impact_score=1, ats_keyword_score=1,
        localization_score=1, completeness_score=1, summary="x",
    )

    def fake(tier, **kw):
        seen["tier"] = tier
        seen["kw"] = kw
        return FakeLLM(canned)

    monkeypatch.setattr(mod, "get_llm", fake)
    mod.evaluate_resume("t", Profile(name="a", summary="b", raw_text="c"))
    assert seen["tier"] == "deep"
    # 健檢輸出大且 deep 為推理模型，max_tokens 必須高於預設 2000，避免截斷
    assert seen["kw"].get("max_tokens", 0) > 2000
    assert seen["kw"]["structured_retries"] == 1


def test_fallback_resume_assessment_is_usable_when_llm_format_breaks():
    profile = Profile(
        name="王小明",
        summary="後端工程師",
        skills=["Python", "FastAPI", "PostgreSQL"],
        raw_text="",
    )
    assessment = mod.fallback_resume_assessment(
        "Python FastAPI 後端工程師\n負責 API 開發，將處理時間降低 30%。",
        profile,
        reason="API key 回覆不是合法 JSON",
    )

    assert isinstance(assessment, ResumeAssessment)
    assert 0 <= assessment.overall_score <= 100
    assert "保守備援" in assessment.summary
    assert assessment.strengths
    assert assessment.issues


def test_fallback_resume_assessment_uses_resume_specific_evidence():
    profile = Profile(
        name="Alex Chen",
        summary="Backend engineer",
        skills=["FastAPI", "PostgreSQL", "AWS", "Redis"],
        experiences=[
            "Built payment API with FastAPI PostgreSQL AWS and reduced latency by 42% for 120k users.",
        ],
        preferred_roles=["Backend Engineer"],
        raw_text="",
    )
    assessment = mod.fallback_resume_assessment(
        "\n".join([
            "Alex Chen",
            "Backend Engineer",
            "Built payment API with FastAPI PostgreSQL AWS and reduced latency by 42% for 120k users.",
            "Led Redis cache migration and cut cloud cost by 18%.",
        ]),
        profile,
        reason="Codex CLI returned invalid JSON",
    )

    combined = " ".join(
        [assessment.summary, *assessment.strengths]
        + [issue.problem + " " + issue.fix for issue in assessment.issues]
        + [rw.original + " " + rw.improved + " " + rw.why for rw in assessment.rewrite_examples]
    )
    assert "42%" in combined
    assert "FastAPI" in combined
    assert "Backend Engineer" in combined
    assert len(assessment.issues) >= 3
    assert len(assessment.rewrite_examples) >= 2
