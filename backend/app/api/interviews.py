from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.db.database import get_db
from backend.app.models.interview import Interview
from backend.app.models.user import User
from backend.app.schemas.interview import InterviewCreate, InterviewRead
from backend.app.services.pdf_extractor import extract_text_from_pdf

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("/", response_model=InterviewRead, status_code=status.HTTP_201_CREATED)
def create_interview(
    interview_in: InterviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "recruiter":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only recruiters can create interviews.",
        )

    interview = Interview(**interview_in.model_dump(), recruiter_id=current_user.id)
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return interview


@router.get("/", response_model=list[InterviewRead])
def list_my_interviews(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        select(Interview)
        .where(Interview.recruiter_id == current_user.id)
        .order_by(Interview.created_at.desc())
    )
    return list(db.scalars(query))


@router.post("/{interview_id}/jd")
def upload_job_description(
    interview_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    interview = db.get(Interview, interview_id)
    if interview is None or interview.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found.",
        )

    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a PDF file.",
        )

    try:
        text = extract_text_from_pdf(file.file.read())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read this PDF.",
        )

    interview.jd_text = text
    db.commit()
    return {"interview_id": interview.id, "characters": len(text), "preview": text[:300]}