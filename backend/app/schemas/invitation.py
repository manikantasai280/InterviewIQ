from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class InvitationCreate(BaseModel):
    """Candidate emails plus the interview start time."""

    emails: list[EmailStr] = Field(min_length=1, max_length=100)
    scheduled_at: datetime


class InvitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    interview_id: int
    candidate_email: EmailStr
    access_code: str
    scheduled_at: datetime
    status: str
    email_sent: bool