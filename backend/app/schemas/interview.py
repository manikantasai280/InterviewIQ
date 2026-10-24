from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InterviewCreate(BaseModel):
    """Data a recruiter sends to create an interview."""

    title: str = Field(min_length=1, max_length=255)
    job_role: str = Field(min_length=1, max_length=255)
    description: str | None = None
    skills: str = Field(min_length=1)


class InterviewRead(BaseModel):
    """Data we send back about an interview."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    job_role: str
    description: str | None
    skills: str
    status: str
    recruiter_id: int
    created_at: datetime