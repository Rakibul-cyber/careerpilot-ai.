# Job-alert HTTP endpoints (v1) — all protected, user-scoped.
#
# Thin transport layer: delegate to JobAlertService, translate domain errors
# (missing saved search -> 404, duplicate alert -> 409, missing alert -> 404).
# The /run endpoint is a manual/dev trigger; a scheduler will call the service
# directly later.

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_job_alert_service
from app.models.user import User
from app.schemas.job_alert import JobAlertCreate, JobAlertRead, JobAlertUpdate
from app.services.job_alert_service import JobAlertService

router = APIRouter(prefix="/job-alerts", tags=["Job Alerts"])


@router.post(
    "",
    response_model=JobAlertRead,
    status_code=status.HTTP_201_CREATED,
)
def create_job_alert(
    data: JobAlertCreate,
    db: Session = Depends(get_db),
    service: JobAlertService = Depends(get_job_alert_service),
    current_user: User = Depends(get_current_user),
) -> JobAlertRead:
    """Create a job alert for one of the current user's saved searches."""
    try:
        return service.create_job_alert(db, current_user.id, data)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found",
        ) from None
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job alert for this saved search already exists",
        ) from None


@router.get("", response_model=list[JobAlertRead])
def list_job_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    service: JobAlertService = Depends(get_job_alert_service),
    current_user: User = Depends(get_current_user),
) -> list[JobAlertRead]:
    """List the current user's job alerts (newest first), paginated."""
    return service.list_job_alerts(db, current_user.id, skip=skip, limit=limit)


@router.get("/{alert_id}", response_model=JobAlertRead)
def get_job_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    service: JobAlertService = Depends(get_job_alert_service),
    current_user: User = Depends(get_current_user),
) -> JobAlertRead:
    """Fetch one of the current user's job alerts by id."""
    alert = service.get_job_alert(db, current_user.id, alert_id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job alert not found",
        )
    return alert


@router.put("/{alert_id}", response_model=JobAlertRead)
def update_job_alert(
    alert_id: UUID,
    data: JobAlertUpdate,
    db: Session = Depends(get_db),
    service: JobAlertService = Depends(get_job_alert_service),
    current_user: User = Depends(get_current_user),
) -> JobAlertRead:
    """Update one of the current user's job alerts."""
    alert = service.update_job_alert(db, current_user.id, alert_id, data)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job alert not found",
        )
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    service: JobAlertService = Depends(get_job_alert_service),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Soft-delete one of the current user's job alerts."""
    alert = service.delete_job_alert(db, current_user.id, alert_id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job alert not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{alert_id}/run")
def run_job_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    service: JobAlertService = Depends(get_job_alert_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Manually run one alert now (dev/manual trigger). Returns match count."""
    alert = service.get_job_alert(db, current_user.id, alert_id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job alert not found",
        )
    matches = service.run_alert(db, alert)
    return {"match_count": len(matches)}
