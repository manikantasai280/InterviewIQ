from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuestionCreate(BaseModel):
    """Data a recruiter sends to add a question."""

    text: str = Field(min_length=1)
    skill: str | None = Field(default=None, max_length=255)


class QuestionRead(BaseModel):
    """Data we send back about a question."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    interview_id: int
    order_number: int
    text: str
    skill: str | None
    source: str
    created_at: datetime
    