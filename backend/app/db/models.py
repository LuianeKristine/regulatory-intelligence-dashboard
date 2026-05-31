from datetime import datetime

from sqlalchemy import JSON, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class Guidance(Base):
    __tablename__ = "guidances"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(1024), nullable=False)
    url = Column(String(2048), unique=True, nullable=False, index=True)
    pdf_url = Column(String(2048), nullable=True)
    fda_center = Column(String(128), nullable=False)
    topic = Column(String(256), nullable=True)
    status = Column(String(64), nullable=False)
    published_date = Column(Date, nullable=True)
    content_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    summary = relationship("GuidanceSummary", back_populates="guidance", uselist=False)


class GuidanceSummary(Base):
    __tablename__ = "guidance_summaries"

    id = Column(Integer, primary_key=True, index=True)
    guidance_id = Column(Integer, ForeignKey("guidances.id", ondelete="CASCADE"), nullable=False, unique=True)
    key_points = Column(JSON, default=list, nullable=False)
    major_changes = Column(JSON, default=list, nullable=False)
    regulatory_impact = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    guidance = relationship("Guidance", back_populates="summary")
