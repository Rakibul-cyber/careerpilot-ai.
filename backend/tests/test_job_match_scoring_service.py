import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.job import Job
from app.models.resume_profile import ResumeProfile
from app.services.job_match_scoring_service import JobMatchScoringService


class JobMatchScoringServiceTests(unittest.TestCase):
    def make_profile(self, **overrides):
        values = {
            "resume_id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "location": "Berlin, Germany",
            "summary": "Backend engineer building Python APIs.",
            "skills": ["Python", "FastAPI", "PostgreSQL", "C++", "Python"],
            "work_experience": [
                {"title": "Backend Engineer"},
                {"title": "Python Developer"},
                {"title": "API Engineer"},
            ],
            "languages": ["English", "German"],
        }
        values.update(overrides)
        return ResumeProfile(**values)

    def make_job(self, **overrides):
        values = {
            "title": "Senior Backend Engineer",
            "normalized_title": "Backend Engineer",
            "company_id": uuid.uuid4(),
            "location": "Berlin",
            "remote_type": "onsite",
            "description": (
                "Build Python and FastAPI services for data products. "
                "The team also maintains C++ integrations."
            ),
            "requirements": (
                "PostgreSQL experience required. English and German language "
                "skills are expected."
            ),
        }
        values.update(overrides)
        return Job(**values)

    def test_scores_strong_match_with_deduped_skills_and_reasons(self):
        result = JobMatchScoringService().score(
            self.make_profile(),
            self.make_job(),
        )

        self.assertEqual(result.overall_score, 100.0)
        self.assertEqual(result.skill_score, 50.0)
        self.assertEqual(result.title_score, 20.0)
        self.assertEqual(result.experience_score, 15.0)
        self.assertEqual(result.location_score, 15.0)
        self.assertEqual(
            result.matched_skills,
            ["C++", "FastAPI", "PostgreSQL", "Python"],
        )
        self.assertEqual(result.missing_skills, [])
        self.assertEqual(result.risk_flags, [])
        self.assertEqual(result.raw_match_data["skills"]["matched_count"], 4)
        self.assertEqual(
            result.raw_match_data["title"]["matched_terms"],
            ["backend", "engineer"],
        )
        self.assertEqual(
            result.raw_match_data["location_language"]["language"],
            "2/2",
        )

    def test_flags_low_information_profile_and_location_language_risks(self):
        result = JobMatchScoringService().score(
            self.make_profile(
                location="Madrid",
                skills=[],
                work_experience=[],
                languages=["Spanish"],
                summary=None,
            ),
            self.make_job(
                location="Berlin",
                description="Backend platform role.",
                requirements="German required.",
            ),
        )

        self.assertEqual(result.skill_score, 0.0)
        self.assertEqual(result.experience_score, 0.0)
        self.assertEqual(result.location_score, 0.0)
        self.assertIn("no_skills_on_profile", result.risk_flags)
        self.assertIn("no_work_experience", result.risk_flags)
        self.assertIn("location_mismatch", result.risk_flags)
        self.assertIn("language_requirement_unmet", result.risk_flags)
        self.assertEqual(
            result.raw_match_data["location_language"]["required_languages"],
            ["german"],
        )

    def test_remote_job_and_missing_language_requirement(self):
        result = JobMatchScoringService().score(
            self.make_profile(location=None, languages=["English"]),
            self.make_job(
                location=None,
                remote_type="remote",
                requirements="French and English are required.",
            ),
        )

        self.assertEqual(
            result.raw_match_data["location_language"]["location"],
            "remote_or_unspecified",
        )
        self.assertEqual(
            result.raw_match_data["location_language"]["required_languages"],
            ["english", "french"],
        )
        self.assertEqual(
            result.raw_match_data["location_language"]["candidate_languages"],
            ["english"],
        )
        self.assertIn("language_requirement_unmet", result.risk_flags)


if __name__ == "__main__":
    unittest.main()
