from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.db.database import get_db
from backend.app.models.interview import Interview
from backend.app.models.question import Question
from backend.app.models.user import User
from backend.app.schemas.question import QuestionCreate, QuestionRead

router = APIRouter(prefix="/interviews/{interview_id}/questions", tags=["questions"])


def get_owned_interview(interview_id: int, user: User, db: Session) -> Interview:
    """Return the interview only if it exists and belongs to this user."""
    interview = db.get(Interview, interview_id)
    if interview is None or interview.recruiter_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found.",
        )
    return interview


@router.post("/", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
def add_question(
    interview_id: int,
    question_in: QuestionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    interview = get_owned_interview(interview_id, current_user, db)

    last_number = db.scalar(
        select(func.max(Question.order_number)).where(
            Question.interview_id == interview.id
        )
    )
    question = Question(
        **question_in.model_dump(),
        interview_id=interview.id,
        order_number=(last_number or 0) + 1,
        source="manual",
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.get("/", response_model=list[QuestionRead])
def list_questions(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    interview = get_owned_interview(interview_id, current_user, db)
    query = (
        select(Question)
        .where(Question.interview_id == interview.id)
        .order_by(Question.order_number)
    )
    return list(db.scalars(query))