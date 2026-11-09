from typing import TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph

from backend.app.core.config import settings
from backend.app.services.email_service import send_email


class InviteState(TypedDict):  # the shared notebook
    interview_title: str
    job_role: str
    interview_id: int
    candidates: list[dict]  # each has: email, access_code, when
    intro: str
    sent: list[str]
    failed: list[str]


def write_node(state: InviteState):
    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model, google_api_key=settings.gemini_api_key, timeout=60
    )
    reply = llm.invoke(
        f"Write a warm, professional 2-sentence invitation to an AI interview for "
        f"a {state['job_role']} role called '{state['interview_title']}'. "
        "Do not include dates, codes, a greeting line or a sign-off."
    )
    return {"intro": str(reply.text).strip()}


def send_node(state: InviteState):
    sent, failed = [], []
    for c in state["candidates"]:
        body = (
            f"Hello,\n\n{state['intro']}\n\n"
            f"Date and time: {c['when']}\n"
            f"Interview ID: {state['interview_id']}\n"
            f"Access code: {c['access_code']}\n\n"
            f"Open {settings.frontend_url}, enter your interview ID and access code, "
            f"and wait for the start time.\n\nGood luck!\nInterviewIQ"
        )
        try:
            send_email(c["email"], f"Interview invitation: {state['interview_title']}", body)
            sent.append(c["email"])
        except Exception:
            failed.append(c["email"])
    return {"sent": sent, "failed": failed}


graph = StateGraph(InviteState)
graph.add_node("write", write_node)
graph.add_node("send", send_node)
graph.add_edge(START, "write")
graph.add_edge("write", "send")
graph.add_edge("send", END)
invite_agent = graph.compile()