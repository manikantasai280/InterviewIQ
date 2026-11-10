from typing import Literal, TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from backend.app.core.config import settings

# Safety ceilings only (a bug can never loop forever). Gemini decides inside them.
HARD_MAX_PER_SKILL = 10
HARD_MAX_QUESTIONS = 40
MAX_REVIEW_ROUNDS = 2   # how many times the critic may send a score back
START_LEVEL = 3

LEVELS = {
    1: "basic definitions and concepts",
    2: "fundamentals applied to simple examples",
    3: "practical, intermediate real-world usage",
    4: "advanced design, trade-offs and debugging",
    5: "expert level: internals, edge cases, scaling, and failure modes",
}


class QuestionPlan(BaseModel):
    question: str
    key_points: list[str]           # the answer key: what a good answer covers


class Review(BaseModel):
    score: int                      # 1-10
    evidence: str                   # short quote from the answer that justifies the score
    feedback: str
    skill_level_estimate: int       # 1-5
    skill_confident: bool
    action: Literal["harder", "easier", "follow_up", "next_skill"]
    finish_interview: bool


class Verdict(BaseModel):
    agrees: bool
    problem: str                    # what is wrong with the grading (empty if agrees)
    corrected_score: int            # the score the critic thinks is fair, 1-10


class InterviewState(TypedDict):    # the notebook
    job_role: str
    skills: list[str]
    skill_index: int
    level: int
    history: list[dict]
    skill_results: dict
    answer: str | None
    action: str
    finish: bool
    time_up: bool
    next_question: str
    finished: bool
    review: dict
    critic_note: str
    critic_agrees: bool
    corrected_score: int
    review_round: int


def _llm():
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model, google_api_key=settings.gemini_api_key, timeout=60
    )


def evaluate_node(state: InterviewState):
    """GRADER: score the answer against the answer key."""
    history = [dict(h) for h in state["history"]]
    last = history[-1]
    skill = last["skill"]
    last["answer"] = state["answer"]

    skill_log = "\n".join(
        f"- [level {h['level']}] Q: {h['question']} | A: {h['answer']} | score: {h['score']}"
        for h in history
        if h["skill"] == skill and h["score"] is not None
    ) or "(none yet)"

    objection = state.get("critic_note") or ""
    objection_text = (
        f"\nA reviewer objected to your previous grading: {objection}\n"
        "Reconsider carefully and fix the grading if the objection is fair.\n"
        if objection else ""
    )

    review = _llm().with_structured_output(Review).invoke(
        f"You are an expert adaptive interviewer for a {state['job_role']} role.\n"
        f"Skill: {skill}. Question level: {last['level']} of 5.\n"
        f"Earlier answers on this skill:\n{skill_log}\n\n"
        f"Question: {last['question']}\n"
        f"Answer key (what a good answer covers): {last.get('key_points')}\n"
        f"Candidate answer: {state['answer']}\n{objection_text}\n"
        "Grade ONLY against the answer key. Score 1-10. In 'evidence', quote the part of "
        "the answer that justifies your score (write 'nothing relevant' if there is none). "
        "Give one or two sentences of feedback. Estimate the skill level (1-5) shown overall. "
        "Choose the next action: harder (answered well), easier (struggling), follow_up "
        "(vague or partly right), next_skill (you know their level). Set skill_confident "
        "true only with enough evidence about this skill, and finish_interview true only "
        "with enough evidence about the whole candidate. Be efficient."
    )
    return {"history": history, "review": review.model_dump()}


def verify_node(state: InterviewState):
    """CRITIC: check the grader's score for fairness."""
    last = state["history"][-1]
    r = state["review"]
    verdict = _llm().with_structured_output(Verdict).invoke(
        "You are a senior reviewer checking another interviewer's grading.\n"
        f"Question: {last['question']}\nAnswer key: {last.get('key_points')}\n"
        f"Candidate answer: {state['answer']}\n"
        f"Grader's score: {r['score']}/10. Evidence quoted: {r['evidence']}\n"
        f"Grader's feedback: {r['feedback']}\n\n"
        "Is the score fair given the answer key? Check that the quoted evidence really "
        "appears in the answer and really supports the score. Watch for scores that are "
        "too generous or too harsh. If the score is within about 1 point of fair, agree. "
        "Otherwise say what is wrong and give the corrected score."
    )
    return {
        "critic_agrees": verdict.agrees,
        "critic_note": "" if verdict.agrees else verdict.problem,
        "corrected_score": verdict.corrected_score,
        "review_round": state.get("review_round", 0) + 1,
    }


def commit_node(state: InterviewState):
    """Save the final score once grader and critic are settled."""
    history = [dict(h) for h in state["history"]]
    last = history[-1]
    skill = last["skill"]
    r = state["review"]

    if state["critic_agrees"]:
        score = r["score"]
    else:  # still disagree after the allowed rounds: average the two views
        score = round((r["score"] + state["corrected_score"]) / 2)
    score = max(1, min(10, score))

    last["score"] = score
    last["feedback"] = r["feedback"]
    last["evidence"] = r["evidence"]

    results = dict(state["skill_results"])
    results[skill] = {
        "level": max(1, min(5, r["skill_level_estimate"])),
        "confident": r["skill_confident"],
    }
    return {
        "history": history,
        "skill_results": results,
        "action": "next_skill" if r["skill_confident"] else r["action"],
        "finish": r["finish_interview"],
        "critic_note": "",
        "review_round": 0,
    }


def decide_node(state: InterviewState):
    index, level = state["skill_index"], state["level"]
    skill = state["skills"][index]
    asked_here = sum(1 for h in state["history"] if h["skill"] == skill)
    action = state["action"]
    if asked_here >= HARD_MAX_PER_SKILL:
        action = "next_skill"

    if action == "harder":
        level = min(level + 1, 5)
    elif action == "easier":
        level = max(level - 1, 1)
    elif action == "next_skill":
        level = state["skill_results"].get(skill, {}).get("level", level)
        index += 1

    finished = (
        state["finish"]
        or state["time_up"]
        or index >= len(state["skills"])
        or len(state["history"]) >= HARD_MAX_QUESTIONS
    )
    return {"skill_index": index, "level": level, "action": action, "finished": finished}


def ask_node(state: InterviewState):
    history = [dict(h) for h in state["history"]]
    skill = state["skills"][state["skill_index"]]
    level = state["level"]

    if state.get("action") == "follow_up" and history:
        last = history[-1]
        prompt = (
            f"You are interviewing for a {state['job_role']} role. Skill: {skill}.\n"
            f"You asked: {last['question']}\nThey answered: {last['answer']}\n"
            "Write ONE short follow-up question that digs into the weak or vague part "
            "of that answer, plus the key points a good answer must cover."
        )
    else:
        asked = [h["question"] for h in history if h["skill"] == skill]
        prompt = (
            f"You are interviewing for a {state['job_role']} role. Skill: {skill}.\n"
            f"Write ONE open-ended question at level {level} of 5 ({LEVELS[level]}), "
            f"plus the key points a good answer must cover.\n"
            f"Do not repeat these earlier questions: {asked}"
        )

    plan = _llm().with_structured_output(QuestionPlan).invoke(prompt)
    history.append(
        {"skill": skill, "level": level, "question": plan.question.strip(),
         "key_points": plan.key_points, "answer": None, "score": None,
         "feedback": None, "evidence": None}
    )
    return {"history": history, "next_question": plan.question.strip()}


def route_start(state: InterviewState):
    return "evaluate" if state.get("answer") else "ask"


def route_after_verify(state: InterviewState):
    if not state["critic_agrees"] and state["review_round"] < MAX_REVIEW_ROUNDS:
        return "evaluate"   # the loop: grade again with the critic's objection
    return "commit"


def route_after_decide(state: InterviewState):
    return END if state["finished"] else "ask"


graph = StateGraph(InterviewState)
graph.add_node("evaluate", evaluate_node)
graph.add_node("verify", verify_node)
graph.add_node("commit", commit_node)
graph.add_node("decide", decide_node)
graph.add_node("ask", ask_node)
graph.add_conditional_edges(START, route_start, {"evaluate": "evaluate", "ask": "ask"})
graph.add_edge("evaluate", "verify")
graph.add_conditional_edges(
    "verify", route_after_verify, {"evaluate": "evaluate", "commit": "commit"}
)
graph.add_edge("commit", "decide")
graph.add_conditional_edges("decide", route_after_decide, {END: END, "ask": "ask"})
graph.add_edge("ask", END)
interview_agent = graph.compile()