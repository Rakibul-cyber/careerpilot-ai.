# Saved-search HTTP endpoints (v1) — all protected, user-scoped CRUD.
#
# Thin transport layer: delegate to SavedSearchService, translate domain errors
# (duplicate name -> 409, missing/foreign row -> 404). Ownership is enforced in
# the service by scoping every operation to current_user.id.

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_saved_search_service
from app.models.user import User
from app.schemas.saved_search import (
    SavedSearchCreate,
    SavedSearchRead,
    SavedSearchUpdate,
)
from app.services.saved_search_service import SavedSearchService

router = APIRouter(prefix="/saved-searches", tags=["Saved Searches"])


@router.post(
    "",
    response_model=SavedSearchRead,
    status_code=status.HTTP_201_CREATED,
)
def create_saved_search(
    data: SavedSearchCreate,
    db: Session = Depends(get_db),
    service: SavedSearchService = Depends(get_saved_search_service),
    current_user: User = Depends(get_current_user),
) -> SavedSearchRead:
    """Create a saved search for the current user."""
    try:
        return service.create_saved_search(db, current_user.id, data)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Saved search with this name already exists",
        ) from None


@router.get("", response_model=list[SavedSearchRead])
def list_saved_searches(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    service: SavedSearchService = Depends(get_saved_search_service),
    current_user: User = Depends(get_current_user),
) -> list[SavedSearchRead]:
    """List the current user's saved searches (newest first), paginated."""
    return service.list_saved_searches(db, current_user.id, skip=skip, limit=limit)


@router.get("/{saved_search_id}", response_model=SavedSearchRead)
def get_saved_search(
    saved_search_id: UUID,
    db: Session = Depends(get_db),
    service: SavedSearchService = Depends(get_saved_search_service),
    current_user: User = Depends(get_current_user),
) -> SavedSearchRead:
    """Fetch one of the current user's saved searches by id."""
    saved_search = service.get_saved_search(db, current_user.id, saved_search_id)
    if saved_search is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found",
        )
    return saved_search


@router.put("/{saved_search_id}", response_model=SavedSearchRead)
def update_saved_search(
    saved_search_id: UUID,
    data: SavedSearchUpdate,
    db: Session = Depends(get_db),
    service: SavedSearchService = Depends(get_saved_search_service),
    current_user: User = Depends(get_current_user),
) -> SavedSearchRead:
    """Update one of the current user's saved searches."""
    try:
        saved_search = service.update_saved_search(
            db, current_user.id, saved_search_id, data
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Saved search with this name already exists",
        ) from None
    if saved_search is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found",
        )
    return saved_search


@router.delete("/{saved_search_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_search(
    saved_search_id: UUID,
    db: Session = Depends(get_db),
    service: SavedSearchService = Depends(get_saved_search_service),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Soft-delete one of the current user's saved searches."""
    saved_search = service.delete_saved_search(db, current_user.id, saved_search_id)
    if saved_search is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved search not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
