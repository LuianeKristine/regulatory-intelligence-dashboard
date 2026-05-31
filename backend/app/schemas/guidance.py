from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class GuidanceBase(BaseModel):
    title: str
    url: HttpUrl
    pdf_url: Optional[HttpUrl] = None
    fda_center: str
    topic: Optional[str] = None
    status: str
    published_date: Optional[date] = None
    content_hash: str


class GuidanceCreate(GuidanceBase):
    pass


class GuidanceUpdate(BaseModel):
    title: Optional[str] = None
    pdf_url: Optional[HttpUrl] = None
    fda_center: Optional[str] = None
    topic: Optional[str] = None
    status: Optional[str] = None
    published_date: Optional[date] = None
    content_hash: Optional[str] = None


class GuidanceSummaryRead(BaseModel):
    key_points: List[str]
    major_changes: List[str]
    regulatory_impact: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True


class GuidanceRead(GuidanceBase):
    id: int
    created_at: datetime
    updated_at: datetime
    summary: Optional[GuidanceSummaryRead] = None

    class Config:
        orm_mode = True
