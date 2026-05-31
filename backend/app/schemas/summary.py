from typing import List, Optional

from pydantic import BaseModel


class GuidanceSummaryCreate(BaseModel):
    guidance_id: int
    key_points: List[str]
    major_changes: List[str]
    regulatory_impact: Optional[str] = None


class GuidanceSummaryRead(BaseModel):
    key_points: List[str]
    major_changes: List[str]
    regulatory_impact: Optional[str] = None
    created_at: str

    class Config:
        orm_mode = True
