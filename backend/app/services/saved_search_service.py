# Business-logic layer for the SavedSearch aggregate.
#
# Enforces per-user ownership and unique saved-search names. All operations are
# scoped by user_id so a user can only ever touch their own saved searches.

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.saved_search import SavedSearch
from app.repositories.saved_search_repository import SavedSearchRepository
from app.schemas.saved_search import SavedSearchCreate, SavedSearchUpdate


class SavedSearchService:
    def __init__(
        self, saved_search_repository: SavedSearchRepository | None = None
    ) -> None:
        self.saved_search_repository = (
            saved_search_repository or SavedSearchRepository()
        )

    def create_saved_search(
        self, db: Session, user_id: UUID, data: SavedSearchCreate
    ) -> SavedSearch:
        if (
            self.saved_search_repository.get_by_name(db, user_id, data.name)
            is not None
        ):
            raise ValueError("Saved search with this name already exists")

        saved_search = SavedSearch(user_id=user_id, **data.model_dump())
        return self.saved_search_repository.create(db, saved_search)

    def get_saved_search(
        self, db: Session, user_id: UUID, saved_search_id: UUID
    ) -> SavedSearch | None:
        return self.saved_search_repository.get_by_id(
            db, saved_search_id, user_id
        )

    def list_saved_searches(
        self, db: Session, user_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[SavedSearch]:
        return self.saved_search_repository.list_by_user(
            db, user_id, skip=skip, limit=limit
        )

    def update_saved_search(
        self,
        db: Session,
        user_id: UUID,
        saved_search_id: UUID,
        data: SavedSearchUpdate,
    ) -> SavedSearch | None:
        saved_search = self.saved_search_repository.get_by_id(
            db, saved_search_id, user_id
        )
        if saved_search is None:
            return None

        fields = data.model_dump(exclude_unset=True)

        new_name = fields.get("name")
        if new_name is not None and new_name != saved_search.name:
            existing = self.saved_search_repository.get_by_name(
                db, user_id, new_name
            )
            if existing is not None and existing.id != saved_search.id:
                raise ValueError("Saved search with this name already exists")

        for field, value in fields.items():
            setattr(saved_search, field, value)

        return self.saved_search_repository.update(db, saved_search)

    def delete_saved_search(
        self, db: Session, user_id: UUID, saved_search_id: UUID
    ) -> SavedSearch | None:
        saved_search = self.saved_search_repository.get_by_id(
            db, saved_search_id, user_id
        )
        if saved_search is None:
            return None
        return self.saved_search_repository.soft_delete(db, saved_search)
