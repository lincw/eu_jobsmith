from app.agents.skill_gap import analyze_skill_gap
from app.models import Profile, JobPosting


def test_gap_and_demand():
    jobs = [
        JobPosting(source="x", title="t", company="c", url="u", requirements=["Python", "LLM"]),
        JobPosting(source="x", title="t", company="c", url="u2", requirements=["Python", "Docker"]),
    ]
    prof = Profile(name="a", summary="", skills=["Python"], raw_text="")
    rep = analyze_skill_gap(prof, jobs)
    demand = {d.skill: d.count for d in rep.top_demand}
    assert demand["Python"] == 2
    gaps = {g.skill for g in rep.your_gaps}
    assert "LLM" in gaps and "Docker" in gaps and "Python" not in gaps   # 已具備不算缺口
    assert "Python" in rep.have


def test_case_insensitive_and_empty():
    jobs = [JobPosting(source="x", title="t", company="c", url="u", requirements=["python", ""])]
    prof = Profile(name="a", summary="", skills=["PYTHON"], raw_text="")
    rep = analyze_skill_gap(prof, jobs)
    assert not rep.your_gaps                # python 已具備（大小寫不敏感），空字串忽略
    assert rep.top_demand[0].skill == "python"
