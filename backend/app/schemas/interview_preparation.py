# Pydantic v2 schemas for InterviewPreparation.

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.interview_preparation import (
    InterviewDifficulty,
    InterviewPreparationStatus,
)


class InterviewPreparationPoint(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    reason: str = Field(min_length=1, max_length=1000)

    model_config = ConfigDict(extra="forbid")


class InterviewQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=1000)
    difficulty: InterviewDifficulty

    model_config = ConfigDict(extra="forbid")


class StudyTopic(BaseModel):
    topic: str = Field(min_length=1, max_length=300)
    reason: str = Field(min_length=1, max_length=1000)
    priority: InterviewDifficulty

    model_config = ConfigDict(extra="forbid")


class InterviewTip(BaseModel):
    tip: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=1000)

    model_config = ConfigDict(extra="forbid")


class InterviewPreparationAIOutput(BaseModel):
    """Strict shape expected from the interview-preparation AI client."""

    summary: str = Field(min_length=1, max_length=4000)
    strengths: list[InterviewPreparationPoint] = Field(min_length=1)
    weaknesses: list[InterviewPreparationPoint] = Field(min_length=1)
    technical_questions: list[InterviewQuestion] = Field(min_length=1)
    behavioral_questions: list[InterviewQuestion] = Field(min_length=1)
    company_questions: list[InterviewQuestion] = Field(min_length=1)
    study_topics: list[StudyTopic] = Field(min_length=1)
    interview_tips: list[InterviewTip] = Field(min_length=1)
    estimated_difficulty: InterviewDifficulty

    model_config = ConfigDict(extra="forbid")

    @field_validator("summary")
    @classmethod
    def _strip_summary(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("summary is empty")
        return value


class InterviewPreparationRead(BaseModel):
    """Public view of an interview preparation package."""

    id: UUID
    user_id: UUID
    application_id: UUID
    generation_status: InterviewPreparationStatus
    generation_error: str | None
    summary: str | None
    strengths: list | None
    weaknesses: list | None
    technical_questions: list | None
    behavioral_questions: list | None
    company_questions: list | None
    study_topics: list | None
    interview_tips: list | None
    estimated_difficulty: InterviewDifficulty | None
    generated_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
