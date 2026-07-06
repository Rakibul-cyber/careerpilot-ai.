# Status-transition rules for the ATS Application lifecycle.

from app.models.application import ApplicationStatus


class InvalidApplicationStatusTransitionError(Exception):
    """Raised when a status change is not allowed by the lifecycle."""


class InvalidInitialApplicationStatusError(Exception):
    """Raised when an application is created in an unsupported status."""


class ApplicationStatusTransitionService:
    """Validates Application status changes in one maintainable place."""

    _initial_statuses = frozenset(
        {
            ApplicationStatus.DRAFT,
            ApplicationStatus.READY,
        }
    )

    _allowed = {
        ApplicationStatus.DRAFT: frozenset(
            {
                ApplicationStatus.READY,
                ApplicationStatus.WITHDRAWN,
            }
        ),
        ApplicationStatus.READY: frozenset(
            {
                ApplicationStatus.DRAFT,
                ApplicationStatus.APPLIED,
                ApplicationStatus.WITHDRAWN,
            }
        ),
        ApplicationStatus.APPLIED: frozenset(
            {
                ApplicationStatus.VIEWED,
                ApplicationStatus.PHONE_SCREEN,
                ApplicationStatus.REJECTED,
                ApplicationStatus.WITHDRAWN,
            }
        ),
        ApplicationStatus.VIEWED: frozenset(
            {
                ApplicationStatus.PHONE_SCREEN,
                ApplicationStatus.REJECTED,
                ApplicationStatus.WITHDRAWN,
            }
        ),
        ApplicationStatus.PHONE_SCREEN: frozenset(
            {
                ApplicationStatus.TECHNICAL_INTERVIEW,
                ApplicationStatus.HR_INTERVIEW,
                ApplicationStatus.REJECTED,
                ApplicationStatus.WITHDRAWN,
            }
        ),
        ApplicationStatus.TECHNICAL_INTERVIEW: frozenset(
            {
                ApplicationStatus.HR_INTERVIEW,
                ApplicationStatus.FINAL_INTERVIEW,
                ApplicationStatus.REJECTED,
                ApplicationStatus.WITHDRAWN,
            }
        ),
        ApplicationStatus.HR_INTERVIEW: frozenset(
            {
                ApplicationStatus.TECHNICAL_INTERVIEW,
                ApplicationStatus.FINAL_INTERVIEW,
                ApplicationStatus.REJECTED,
                ApplicationStatus.WITHDRAWN,
            }
        ),
        ApplicationStatus.FINAL_INTERVIEW: frozenset(
            {
                ApplicationStatus.OFFER,
                ApplicationStatus.REJECTED,
                ApplicationStatus.WITHDRAWN,
            }
        ),
        ApplicationStatus.OFFER: frozenset(
            {
                ApplicationStatus.ACCEPTED,
                ApplicationStatus.REJECTED,
                ApplicationStatus.WITHDRAWN,
            }
        ),
        ApplicationStatus.ACCEPTED: frozenset(),
        ApplicationStatus.REJECTED: frozenset(),
        ApplicationStatus.WITHDRAWN: frozenset(),
    }

    def validate_initial(self, status: ApplicationStatus) -> None:
        if status not in self._initial_statuses:
            raise InvalidInitialApplicationStatusError(
                f"Application cannot be created with status {status.value}"
            )

    def validate_transition(
        self, current: ApplicationStatus, target: ApplicationStatus
    ) -> None:
        if current == target:
            return
        if target not in self._allowed[current]:
            raise InvalidApplicationStatusTransitionError(
                f"Invalid application status transition: "
                f"{current.value} -> {target.value}"
            )
