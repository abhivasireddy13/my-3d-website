from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String
from app.db.postgres import Base


class DimProduct(Base):
    """Product dimension. product_key=1 ('Unspecified') is the default surrogate."""

    __tablename__ = "dim_product"

    product_key = Column(Integer, primary_key=True, autoincrement=True)
    product_name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
