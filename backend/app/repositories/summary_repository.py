from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import GuidanceSummary
from app.schemas.summary import GuidanceSummaryCreate


class GuidanceSummaryRepository:
    def get_by_guidance_id(self, db: Session, guidance_id: int) -> Optional[GuidanceSummary]:
        return db.query(GuidanceSummary).filter(GuidanceSummary.guidance_id == guidance_id).first()

    def create_or_update(self, db: Session, summary_in: GuidanceSummaryCreate) -> GuidanceSummary:
        summary = self.get_by_guidance_id(db, summary_in.guidance_id)
        if summary is None:
            summary = GuidanceSummary(**summary_in.dict())
            db.add(summary)
        else:
            summary.key_points = summary_in.key_points
            summary.major_changes = summary_in.major_changes
            summary.regulatory_impact = summary_in.regulatory_impact

        db.commit()
        db.refresh(summary)
        return summary
