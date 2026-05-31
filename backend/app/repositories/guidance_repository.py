from datetime import date
from typing import Iterable, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Guidance
from app.schemas.guidance import GuidanceCreate, GuidanceUpdate


class GuidanceRepository:
    def list(
        self,
        db: Session,
        center: Optional[str] = None,
        status: Optional[str] = None,
        published_from: Optional[date] = None,
        published_to: Optional[date] = None,
        search: Optional[str] = None,
    ) -> List[Guidance]:
        query = db.query(Guidance)

        if center:
            query = query.filter(func.lower(Guidance.fda_center) == center.lower())

        if status:
            query = query.filter(func.lower(Guidance.status) == status.lower())

        if published_from:
            query = query.filter(Guidance.published_date >= published_from)

        if published_to:
            query = query.filter(Guidance.published_date <= published_to)

        if search:
            pattern = f"%{search.lower()}%"
            query = query.filter(
                func.lower(Guidance.title).like(pattern)
                | func.lower(Guidance.topic).like(pattern)
                | func.lower(Guidance.fda_center).like(pattern)
            )

        return query.order_by(Guidance.published_date.desc(), Guidance.updated_at.desc()).all()

    def get_by_id(self, db: Session, guidance_id: int) -> Optional[Guidance]:
        return db.query(Guidance).filter(Guidance.id == guidance_id).first()

    def get_by_url(self, db: Session, url: str) -> Optional[Guidance]:
        return db.query(Guidance).filter(Guidance.url == url).first()

    def create(self, db: Session, guidance_in: GuidanceCreate) -> Guidance:
        guidance = Guidance(**guidance_in.dict())
        db.add(guidance)
        db.commit()
        db.refresh(guidance)
        return guidance

    def update(self, db: Session, guidance: Guidance, updates: GuidanceUpdate) -> Guidance:
        for field, value in updates.dict(exclude_unset=True).items():
            setattr(guidance, field, value)
        db.add(guidance)
        db.commit()
        db.refresh(guidance)
        return guidance

    def delete_by_url(self, db: Session, url: str) -> None:
        guidance = self.get_by_url(db, url)
        if guidance:
            db.delete(guidance)
            db.commit()

    def get_all_urls(self, db: Session) -> Iterable[str]:
        return [row.url for row in db.query(Guidance.url).all()]
