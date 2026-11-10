from typing import Literal, TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from backend.app.core.config import settings


class Verdict(BaseModel):
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    recommendation: Literal["strong_hire", "hire", "maybe", "no_hire"]


class ScoreState(TypedDict):
    job_role: str
    history: list[dict]
    skill_results: dict
    skills: list[dict]
    overall_percent: int
    questions_answered: int
    verdict: dict
    scorecard: dict


def compute_node(state: ScoreState):
    by_skill: dict[str, list[dict]] = {}
    for h in state["history"]:
        if h.get("score") is not None:
            by_skill.setdefault(h["skill"], []).append(h)

    skills, all_scores = [], []
    for skill, items in by_skill.items():
        scores = [h["score"] for h in items]
        all_scores += scores
        best = max(items, key=lambda h: h["score"])
        skills.append(
            {
                "skill": skill,
                "level_reached": state["skill_results"].get(skill, {}).get("level"),
                "average_score": round(sum(scores) / len(scores), 1),
                "questions_asked": len(scores),
                "best_evidence": best.get("evidence"),
            }
        )

    overall = round(sum(all_scores) / len(all_scores) * 10) if all_scores else 0
    return {
        "skills": skills,
        "overall_percent": overall,
        "questions_answered": len(all_scores),
    }


def summarize_node(state: ScoreState):
    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model, google_api_key=settings.gemini_api_key, timeout=60
    )
    verdict = llm.with_structured_output(Verdict).invoke(
        f"You are a hiring analyst. Role: {state['job_role']}.\n"
        f"Overall score: {state['overall_percent']}%. "
        f"Questions answered: {state['questions_answered']}.\n"
        f"Per-skill results (level 1-5, scores 1-10): {state['skills']}\n\n"
        "Write a 3-sentence summary of this candidate, 2-4 strengths, 2-4 weaknesses, "
        "and a recommendation. Use ONLY the results above and do not invent facts."
    )
    v = verdict.model_dump()
    return {
        "verdict": v,
        "scorecard": {
            "overall_percent": state["overall_percent"],
            "questions_answered": state["questions_answered"],
            "skills": state["skills"],
            **v,
        },
    }


graph = StateGraph(ScoreState)
graph.add_node("compute", compute_node)
graph.add_node("summarize", summarize_node)
graph.add_edge(START, "compute")
graph.add_edge("compute", "summarize")
graph.add_edge("summarize", END)
scorecard_agent = graph.compile()


def build_scorecard(job_role: str, history: list, skill_results: dict) -> dict:
    result = scorecard_agent.invoke(
        {"job_role": job_role, "history": history, "skill_results": skill_results}
    )
    return result["scorecard"]