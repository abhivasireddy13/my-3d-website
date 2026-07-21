from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String
from app.db.postgres import Base


class DimRegion(Base):
    """Region dimension. region_key=1 ('Unspecified') is the default surrogate."""

    __tablename__ = "dim_region"

    region_key = Column(Integer, primary_key=True, autoincrement=True)
    region_name = Column(String, nullable=False)
    country = Column(String, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
