from app.models import CompanyBrief
from app.agents import company as company_mod
from tests.conftest import FakeLLM


def test_research_company_summarizes_results(monkeypatch):
    monkeypatch.setattr(
        company_mod, "search_web",
        lambda q, **k: [{"title": "評價", "url": "https://x/a", "content": "福利好"}],
    )
    canned = CompanyBrief(company="未來智能", salary_range="月薪 6 萬起", benefits=["彈性工時"])
    monkeypatch.setattr(company_mod, "get_llm", lambda tier: FakeLLM(canned))

    brief = company_mod.research_company("未來智能")

    assert isinstance(brief, CompanyBrief)
    assert brief.data_limited is False
    assert "彈性工時" in brief.benefits


def test_research_company_marks_data_limited_on_empty(monkeypatch):
    monkeypatch.setattr(company_mod, "search_web", lambda q, **k: [])
    def boom(tier):
        raise AssertionError("LLM should not be called when no search results")
    monkeypatch.setattr(company_mod, "get_llm", boom)

    brief = company_mod.research_company("查無公司")

    assert brief.company == "查無公司"
    assert brief.data_limited is True


def test_research_company_handles_search_failure(monkeypatch):
    def raise_err(q, **k):
        raise RuntimeError("搜尋失敗")
    monkeypatch.setattr(company_mod, "search_web", raise_err)

    brief = company_mod.research_company("壞掉公司")

    assert brief.data_limited is True
