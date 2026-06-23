"""Supervisor 並行圖：parse -> match -> (proceed: fan-out / stop) -> join。

proceed 時扇出到 resume_tailor 與 company_research（並行）；
company_research 完成後再扇出 cover_letter 與 interview_prep（需 company_brief）；
三個生成節點匯入 join（fan-in barrier）後到 END。
各節點寫入不同 state key，故不需 reducer。
"""
from langgraph.graph import StateGraph, START, END

from app.state import CopilotState
from app.agents.parse import parse_job
from app.agents.match import match_profile
from app.agents.company import research_company
from app.agents.resume import tailor_resume
from app.agents.cover_letter import write_cover_letter
from app.agents.interview import prepare_interview

# 匹配分數門檻：低於此分數即使 LLM 建議續做也提早收手（對應設計規格 §6）。
PROCEED_SCORE_THRESHOLD = 60


def parse_node(state: CopilotState) -> dict:
    return {"parsed_job": parse_job(state["jd_text"])}


def match_node(state: CopilotState) -> dict:
    return {"match_report": match_profile(state["parsed_job"], state["profile"])}


def company_research_node(state: CopilotState) -> dict:
    return {"company_brief": research_company(state["parsed_job"].company)}


def resume_tailor_node(state: CopilotState) -> dict:
    return {"tailored_resume": tailor_resume(state["parsed_job"], state["profile"])}


def cover_letter_node(state: CopilotState) -> dict:
    return {"cover_letter": write_cover_letter(
        state["parsed_job"], state["profile"], state.get("company_brief"))}


def interview_prep_node(state: CopilotState) -> dict:
    return {"interview_kit": prepare_interview(
        state["parsed_job"], state["profile"], state.get("company_brief"))}


def join_node(state: CopilotState) -> dict:
    """fan-in 匯合點：等三個生成節點都完成。"""
    return {}


def route_after_match(state: CopilotState):
    """proceed（通過分數門檻且 LLM 建議）→ 扇出；否則收手。"""
    report = state["match_report"]
    if report.recommend_proceed and report.score >= PROCEED_SCORE_THRESHOLD:
        return ["resume_tailor", "company_research"]
    return "stop"


def build_graph():
    g = StateGraph(CopilotState)
    g.add_node("parse", parse_node)
    g.add_node("match", match_node)
    g.add_node("company_research", company_research_node)
    g.add_node("resume_tailor", resume_tailor_node)
    g.add_node("cover_letter", cover_letter_node)
    g.add_node("interview_prep", interview_prep_node)
    g.add_node("join", join_node)

    g.add_edge(START, "parse")
    g.add_edge("parse", "match")
    g.add_conditional_edges(
        "match",
        route_after_match,
        {
            "resume_tailor": "resume_tailor",
            "company_research": "company_research",
            "stop": END,
        },
    )
    # company_research 完成後扇出需要 company_brief 的兩個節點
    g.add_edge("company_research", "cover_letter")
    g.add_edge("company_research", "interview_prep")
    # fan-in：三個生成節點匯入 join
    g.add_edge("resume_tailor", "join")
    g.add_edge("cover_letter", "join")
    g.add_edge("interview_prep", "join")
    g.add_edge("join", END)
    return g.compile()
