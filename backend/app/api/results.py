from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agents.scorecard_agent import build_scorecard
from backend.app.api.deps import get_current_user
from backend.app.db.database import get_db
from backend.app.models.interview import Interview
from backend.app.models.interview_session import InterviewSession
from backend.app.models.invitation import Invitation
from backend.app.models.user import User

router = APIRouter(prefix="/interviews/{interview_id}/results", tags=["results"])


def _owned_interview(interview_id: int, user: User, db: Session) -> Interview:
    interview = db.get(Interview, interview_id)
    if interview is None or interview.recruiter_id != user.id:
        raise HTTPException(404, "Interview not found.")
    return interview


@router.get("/")
def list_results(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    interview = _owned_interview(interview_id, current_user, db)
    invitations = list(
        db.scalars(select(Invitation).where(Invitation.interview_id == interview.id))
    )
    sessions = {
        s.invitation_id: s
        for s in db.scalars(
            select(InterviewSession).where(
                InterviewSession.invitation_id.in_([i.id for i in invitations])
            )
        )
    }
    rows = []
    for inv in invitations:
        s = sessions.get(inv.id)
        rows.append(
            {
                "invitation_id": inv.id,
                "email": inv.candidate_email,
                "status": s.status if s else inv.status,
                "scorecard": s.scorecard if s else None,
            }
        )
    return rows


@router.post("/{invitation_id}/rebuild")
def rebuild_scorecard(
    interview_id: int,
    invitation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    interview = _owned_interview(interview_id, current_user, db)
    session = db.scalar(
        select(InterviewSession)
        .join(Invitation, Invitation.id == InterviewSession.invitation_id)
        .where(
            Invitation.id == invitation_id,
            Invitation.interview_id == interview.id,
        )
    )
    if session is None or session.status != "completed":
        raise HTTPException(404, "No completed interview found for this candidate.")

    session.scorecard = build_scorecard(
        interview.job_role,
        session.state["history"],
        session.state["skill_results"],
    )
    db.commit()
    return session.scorecard