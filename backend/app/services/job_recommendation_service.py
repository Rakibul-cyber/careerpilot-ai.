# Business-logic layer for job recommendations (M32).
#
# Orchestrates existing pieces — it does NOT reinvent them:
#   * M31 semantic search  -> candidate jobs + semantic_score (0..1)
#   * M29 JobMatch scoring -> match_score (0..100), upserted/reused per job
# and blends them:
#     final_score = semantic_score * 40 + match_score * 0.60   (0..100)
#
# No LLM. Candidates come only from active, non-deleted, embedded jobs (the
# semantic search already enforces that). Re-running upserts one recommendation
# per (profile, job) rather than duplicating.

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.job_recommendation import JobRecommendation
from app.models.resume_profile import ResumeParseStatus, ResumeProfile
from app.repositories.job_recommendation_repository import (
    JobRecommendationRepository,
)
from app.repositories.resume_profile_repository import (
    ResumeProfileRepository,
)
from app.services.job_match_service import JobMatchService
from app.services.semantic_job_search_service import SemanticJobSearchService

logger = get_logger(__name__)

SEMANTIC_WEIGHT = 40.0  # applied to semantic_score in [0, 1]
MATCH_WEIGHT = 0.60     # applied to match_score in [0, 100]


class ResumeProfileNotFoundError(Exception):
    """Profile missing or owned by another user (-> HTTP 404)."""


class ResumeProfileNotCompletedError(Exception):
    """Profile exists but isn't parse-completed (-> HTTP 409)."""


class JobRecommendationNotFoundError(Exception):
    """Recommendation missing or owned by another user (-> HTTP 404)."""


class JobRecommendationService:
    def __init__(
        self,
        resume_profile_repository: ResumeProfileRepository | None = None,
        job_recommendation_repository: (
            JobRecommendationRepository | None
        ) = None,
        semantic_search_service: SemanticJobSearchService | None = None,
        job_match_service: JobMatchService | None = None,
    ) -> None:
        self.resume_profile_repository = (
            resume_profile_repository or ResumeProfileRepository()
        )
        self.job_recommendation_repository = (
            job_recommendation_repository or JobRecommendationRepository()
        )
        self.semantic_search_service = (
            semantic_search_service or SemanticJobSearchService()
        )
        self.job_match_service = job_match_service or JobMatchService()

    def recommend(
        self,
        db: Session,
        user_id: uuid.UUID,
        resume_profile_id: uuid.UUID,
        limit: int = 20,
    ) -> list[JobRecommendation]:
        """Generate ranked recommendations for a completed profile (upsert)."""
        profile = self._require_completed_profile(
            db, user_id, resume_profile_id
        )

        query_text = self._build_query_text(profile)
        # Semantic search already excludes soft-deleted, non-ACTIVE, and
        # un-embedded jobs.
        hits = self.semantic_search_service.search(db, query_text, limit)

        recommendations: list[JobRecommendation] = []
        for job, semantic_score in hits:
            semantic_score = self._semantic_score(semantic_score)
            # Reuse M29: upserts one JobMatch per (profile, job).
            match = self.job_match_service.match(
                db, user_id, resume_profile_id, job.id
            )
            match_score = match.overall_score
            final_score = round(
                semantic_score * SEMANTIC_WEIGHT
                + match_score * MATCH_WEIGHT,
                2,
            )
            recommendations.append(
                self._upsert(
                    db,
                    user_id,
                    resume_profile_id,
                    job.id,
                    match,
                    semantic_score,
                    match_score,
                    final_score,
                )
            )

        recommendations.sort(key=lambda r: r.final_score, reverse=True)
        logger.info(
            "Recommendations generated user_id=%s profile_id=%s count=%d",
            user_id,
            resume_profile_id,
            len(recommendations),
        )
        return recommendations

    def get_recommendation(
        self, db: Session, user_id: uuid.UUID, recommendation_id: uuid.UUID
    ) -> JobRecommendation:
        rec = self.job_recommendation_repository.get_by_id(
            db, recommendation_id, user_id
        )
        if rec is None:
            raise JobRecommendationNotFoundError("Recommendation not found")
        return rec

    def list_recommendations(
        self,
        db: Session,
        user_id: uuid.UUID,
        resume_profile_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[JobRecommendation]:
        # Validate ownership so a cross-user profile 404s instead of returning
        # an empty list.
        profile = self.resume_profile_repository.get_by_id(
            db, resume_profile_id, user_id
        )
        if profile is None:
            raise ResumeProfileNotFoundError("Resume profile not found")
        return self.job_recommendation_repository.list_by_profile(
            db, resume_profile_id, user_id, skip=skip, limit=limit
        )

    # --- helpers -----------------------------------------------------------

    def _upsert(
        self,
        db,
        user_id,
        resume_profile_id,
        job_id,
        match,
        semantic_score,
        match_score,
        final_score,
    ) -> JobRecommendation:
        rec = self.job_recommendation_repository.get_by_profile_job(
            db, resume_profile_id, job_id, user_id
        )
        is_new = rec is None
        if is_new:
            rec = JobRecommendation(
                user_id=user_id,
                resume_profile_id=resume_profile_id,
                job_id=job_id,
            )

        rec.job_match_id = match.id
        rec.semantic_score = round(float(semantic_score), 6)
        rec.match_score = match_score
        rec.final_score = final_score
        rec.recommendation_reasons = self._reasons(
            semantic_score, match_score, match
        )
        rec.risk_flags = match.risk_flags or []
        rec.raw_recommendation_data = {
            "semantic_score": round(float(semantic_score), 6),
            "match_score": match_score,
            "weights": {
                "semantic": SEMANTIC_WEIGHT,
                "match": MATCH_WEIGHT,
            },
            "job_match_id": str(match.id),
        }
        rec.recommended_at = datetime.now(timezone.utc)

        if is_new:
            return self.job_recommendation_repository.create(db, rec)
        return self.job_recommendation_repository.update(db, rec)

    @staticmethod
    def _semantic_score(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _reasons(semantic_score, match_score, match) -> list[str]:
        reasons = [
            f"Semantic similarity {semantic_score:.2f} to your profile.",
            f"Deterministic match score {match_score:.0f}/100.",
        ]
        for r in (match.match_reasons or [])[:2]:
            if isinstance(r, str):
                reasons.append(r)
        return reasons

    @staticmethod
    def _build_query_text(profile: ResumeProfile) -> str:
        parts: list[str] = []
        if profile.summary:
            parts.append(profile.summary)
        if profile.skills:
            parts.append(
                "Skills: " + ", ".join(str(s) for s in profile.skills)
            )
        titles = [
            e.get("title")
            for e in (profile.work_experience or [])
            if isinstance(e, dict) and e.get("title")
        ]
        if titles:
            parts.append("Experience: " + ", ".join(titles))
        if profile.location:
            parts.append("Location: " + profile.location)
        return "\n".join(parts) or "job"

    def _require_completed_profile(self, db, user_id, resume_profile_id):
        profile = self.resume_profile_repository.get_by_id(
            db, resume_profile_id, user_id
        )
        if profile is None:
            raise ResumeProfileNotFoundError("Resume profile not found")
        if profile.parse_status != ResumeParseStatus.COMPLETED:
            raise ResumeProfileNotCompletedError(
                "Resume profile has not completed parsing"
            )
        return profile
