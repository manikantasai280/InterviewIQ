from typing import TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.services.rag_service import retrieve_context


class SkillList(BaseModel):
    role_summary: str
    skills: list[str]


class JDState(TypedDict):
    interview_id: int
    context: list[str]
    role_summary: str
    skills: list[str]


def retrieve_node(state: JDState):
    chunks = []
    for q in ["required technical skills", "responsibilities", "qualifications"]:
        chunks += retrieve_context(state["interview_id"], q, k=3)
    return {"context": list(dict.fromkeys(chunks))}


def extract_node(state: JDState):
    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model, google_api_key=settings.gemini_api_key, timeout=60
    )
    result = llm.with_structured_output(SkillList).invoke(
        "From this job description, give a one-sentence role summary and the "
        "5 to 8 most important technical skills to test in an interview.\n\n"
        + "\n\n".join(state["context"])
    )
    return {"role_summary": result.role_summary, "skills": result.skills}


graph = StateGraph(JDState)
graph.add_node("retrieve", retrieve_node)
graph.add_node("extract", extract_node)
graph.add_edge(START, "retrieve")
graph.add_edge("retrieve", "extract")
graph.add_edge("extract", END)
jd_agent = graph.compile()