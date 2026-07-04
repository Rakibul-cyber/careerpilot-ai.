# Mock connector — returns a fixed set of realistic Germany-style postings.
#
# Used to exercise the connector framework end to end without any external I/O.
# external_id values are stable so re-running dedups instead of duplicating.

from app.connectors.base import BaseJobSourceConnector
from app.models.job import JobSource
from app.schemas.ingestion import RawJobInput


class MockJobConnector(BaseJobSourceConnector):
    """Deterministic in-memory connector for development and tests."""

    @property
    def source_name(self) -> str:
        return "mock"

    def fetch_jobs(self) -> list[RawJobInput]:
        return [
            RawJobInput(
                title="Flutter Developer (m/f/d)",
                company_name="Frankfurt Mobile GmbH",
                location="Frankfurt am Main",
                remote_type="hybrid",
                employment_type="working_student",
                source=JobSource.MANUAL,
                source_url="https://example.com/jobs/mock-flutter-001",
                external_id="mock-flutter-001",
                description="Build cross-platform apps with Flutter and Dart.",
                requirements="Flutter, Dart, REST APIs, Git",
                salary_min=20,
                salary_max=25,
                currency="EUR",
            ),
            RawJobInput(
                title="Python Backend Engineer",
                company_name="Berlin Cloud Systems GmbH",
                location="Berlin",
                remote_type="remote",
                employment_type="full_time",
                source=JobSource.MANUAL,
                source_url="https://example.com/jobs/mock-python-002",
                external_id="mock-python-002",
                description="Design and build APIs with FastAPI and PostgreSQL.",
                requirements="Python, FastAPI, PostgreSQL, Docker",
                salary_min=60000,
                salary_max=85000,
                currency="EUR",
            ),
            RawJobInput(
                title="DevOps / Cloud Engineer (Internship)",
                company_name="Rhein-Main Infrastructure GmbH",
                location="Frankfurt am Main",
                remote_type="onsite",
                employment_type="internship",
                source=JobSource.MANUAL,
                source_url="https://example.com/jobs/mock-devops-003",
                external_id="mock-devops-003",
                description="Support CI/CD pipelines and cloud deployments.",
                requirements="AWS, Docker, Kubernetes, Terraform, CI/CD",
                salary_min=1800,
                salary_max=2200,
                currency="EUR",
            ),
        ]
