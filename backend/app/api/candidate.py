from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agents.interview_agent import START_LEVEL, interview_agent
from backend.app.db.database import get_db
from backend.app.models.interview import Interview
from backend.app.models.interview_session import InterviewSession
from backend.app.models.invitation import Invitation
from backend.app.agents.scorecard_agent import build_scorecard

router = APIRouter(prefix="/candidate", tags=["candidate"])

TIME_LIMIT_MINUTES = 60  # after this, the agent wraps up the interview


class Access(BaseModel):
    interview_id: int
    access_code: str


class AnswerIn(Access):
    answer: str


def _get_invitation(data: Access, db: Session) -> Invitation:
    inv = db.scalar(
        select(Invitation).where(
            Invitation.interview_id == data.interview_id,
            Invitation.access_code == data.access_code,
        )
    )
    if inv is None:  # same message for a wrong ID or a wrong code
        raise HTTPException(404, "Invalid interview ID or access code.")
    return inv


def _get_session(inv: Invitation, db: Session):
    return db.scalar(
        select(InterviewSession).where(InterviewSession.invitation_id == inv.id)
    )


def _pending_question(state: dict):
    for h in reversed(state["history"]):
        if h["answer"] is None:
            return h["question"]
    return None


@router.post("/status")
def interview_status(data: Access, db: Session = Depends(get_db)):
    inv = _get_invitation(data, db)
    session = _get_session(inv, db)
    if session and session.status == "completed":
        return {"status": "completed"}
    seconds = (inv.scheduled_at - datetime.now(timezone.utc)).total_seconds()
    if seconds > 0:
        return {"status": "waiting", "seconds_until_start": int(seconds)}
    return {"status": "in_progress" if session else "ready"}


@router.post("/start")
def start_interview(data: Access, db: Session = Depends(get_db)):
    inv = _get_invitation(data, db)
    now = datetime.now(timezone.utc)
    if inv.scheduled_at > now:
        raise HTTPException(
            403, f"Not started yet. Starts in {int((inv.scheduled_at - now).total_seconds())} seconds."
        )

    session = _get_session(inv, db)
    if session:  # resume, e.g. after a page refresh
        if session.status == "completed":
            return {"finished": True}
        return {"finished": False, "question": _pending_question(session.state)}

    interview = db.get(Interview, inv.interview_id)
    skills = [s.strip() for s in interview.skills.split(",") if s.strip()]
    if not skills:
        raise HTTPException(400, "This interview has no skills yet.")

    result = interview_agent.invoke(
        {
            "job_role": interview.job_role, "skills": skills, "skill_index": 0,
            "level": START_LEVEL, "history": [], "skill_results": {},
            "answer": None, "action": "", "finish": False, "time_up": False,
            "next_question": "", "finished": False, "review": {},
            "critic_note": "", "critic_agrees": True, "corrected_score": 0,
            "review_round": 0,
        }
    )
    db.add(InterviewSession(invitation_id=inv.id, state=result))
    inv.status = "started"
    db.commit()
    return {"finished": False, "question": result["next_question"]}


@router.post("/answer")
def submit_answer(data: AnswerIn, db: Session = Depends(get_db)):
    inv = _get_invitation(data, db)
    session = _get_session(inv, db)
    if session is None:
        raise HTTPException(400, "Interview has not been started.")
    if session.status == "completed":
        return {"finished": True}
    if not data.answer.strip():
        raise HTTPException(422, "Answer cannot be empty.")

    state = dict(session.state)
    state["answer"] = data.answer
    elapsed = (datetime.now(timezone.utc) - session.created_at).total_seconds() / 60
    state["time_up"] = elapsed > TIME_LIMIT_MINUTES

    result = interview_agent.invoke(state)
    result["answer"] = None
    session.state = result  # assigning a new dict is what makes SQLAlchemy save it
    if result["finished"]:
        session.status = "completed"
        inv.status = "completed"
        try:
            interview = db.get(Interview, inv.interview_id)
            session.scorecard = build_scorecard(
                interview.job_role, result["history"], result["skill_results"]
            )
        except Exception:
            # Never lose a finished interview because the report failed.
            # The scorecard stays empty and can be rebuilt later.
            session.scorecard = None
    db.commit()

    if result["finished"]:
        return {"finished": True}
    return {"finished": False, "question": result["next_question"]}