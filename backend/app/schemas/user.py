from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Data required to sign up."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=72)
    role: Literal["recruiter", "candidate"] = "recruiter"


class UserRead(BaseModel):
    """Data we send back. Note: no password field."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: str
    created_at: datetime

class Token(BaseModel):
    """What the login endpoint returns."""

    access_token: str
    token_type: str = "bearer"