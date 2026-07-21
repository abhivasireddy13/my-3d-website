from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String
from app.db.postgres import Base


class DimCustomer(Base):
    """Customer dimension. customer_key=1 ('Unspecified') is the default surrogate."""

    __tablename__ = "dim_customer"

    customer_key = Column(Integer, primary_key=True, autoincrement=True)
    customer_name = Column(String, nullable=False)
    segment = Column(String, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
