import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.db.database import get_db
from backend.app.models.interview import Interview
from backend.app.models.user import User
from backend.app.schemas.interview import InterviewCreate, InterviewRead
from backend.app.services.rag_service import ingest_job_description, retrieve_context

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

    # PyPDFLoader needs a file path, so write the upload to a temp file first.
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    try:
        chunk_count = ingest_job_description(tmp_path, interview.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {"interview_id": interview.id, "chunks_stored": chunk_count}


@router.get("/{interview_id}/jd/search")
def search_job_description(
    interview_id: int,
    query: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    interview = db.get(Interview, interview_id)
    if interview is None or interview.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found.",
        )
    return {"query": query, "chunks": retrieve_context(interview.id, query, k=3)}