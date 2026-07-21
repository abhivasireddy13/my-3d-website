from sqlalchemy import Boolean, Column, Date, SmallInteger, String, Integer
from app.db.postgres import Base


class DimDate(Base):
    """Date dimension — one row per calendar day, keyed by YYYYMMDD integer."""

    __tablename__ = "dim_date"

    date_key = Column(Integer, primary_key=True)   # YYYYMMDD, e.g. 20240601
    full_date = Column(Date, nullable=False, unique=True)
    year = Column(SmallInteger, nullable=False)
    quarter = Column(SmallInteger, nullable=False)  # 1–4
    month = Column(SmallInteger, nullable=False)    # 1–12
    month_name = Column(String(10), nullable=False)
    day = Column(SmallInteger, nullable=False)      # 1–31
    day_of_week = Column(SmallInteger, nullable=False)  # 0 = Monday … 6 = Sunday
    day_name = Column(String(10), nullable=False)
    is_weekend = Column(Boolean, nullable=False)
    week_of_year = Column(SmallInteger, nullable=False)
