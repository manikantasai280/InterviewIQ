import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.db.database import get_db
from backend.app.models.interview import Interview
from backend.app.models.invitation import Invitation
from backend.app.models.user import User
from backend.app.schemas.invitation import InvitationCreate, InvitationRead

router = APIRouter(prefix="/interviews/{interview_id}/invitations", tags=["invitations"])


def _owned_interview(interview_id: int, user: User, db: Session) -> Interview:
    interview = db.get(Interview, interview_id)
    if interview is None or interview.recruiter_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found."
        )
    return interview


@router.post("/", response_model=list[InvitationRead], status_code=status.HTTP_201_CREATED)
def create_invitations(
    interview_id: int,
    data: InvitationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    interview = _owned_interview(interview_id, current_user, db)

    # Skip emails that already have an invitation for this interview
    existing = set(
        db.scalars(
            select(Invitation.candidate_email).where(
                Invitation.interview_id == interview.id
            )
        )
    )
    created = []
    for email in dict.fromkeys(str(e).lower() for e in data.emails):
        if email in existing:
            continue
        invitation = Invitation(
            interview_id=interview.id,
            candidate_email=email,
            access_code=secrets.token_urlsafe(8),
            scheduled_at=data.scheduled_at,
        )
        db.add(invitation)
        created.append(invitation)

    db.commit()
    for inv in created:
        db.refresh(inv)
    return created


@router.get("/", response_model=list[InvitationRead])
def list_invitations(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    interview = _owned_interview(interview_id, current_user, db)
    query = select(Invitation).where(Invitation.interview_id == interview.id)
    return list(db.scalars(query))