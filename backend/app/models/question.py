from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.database import Base
from backend.app.models.interview import Interview  # noqa: F401  (so the interviews table is known)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    interview_id: Mapped[int] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), index=True
    )
    order_number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    skill: Mapped[str | None] = mapped_column(String(255), default=None)
    source: Mapped[str] = mapped_column(String(20), default="manual")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )