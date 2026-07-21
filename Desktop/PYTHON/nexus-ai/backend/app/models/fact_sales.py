from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from app.db.postgres import Base


class FactSales(Base):
    """Fact table — one row per sales event in the star schema."""

    __tablename__ = "fact_sales"

    # Integer (not BigInteger) so SQLite treats it as a true rowid alias,
    # enabling autoincrement in the test database. PostgreSQL uses SERIAL.
    sale_key = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("upload_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date_key = Column(
        Integer, ForeignKey("dim_date.date_key"), nullable=False, index=True
    )
    product_key = Column(
        Integer, ForeignKey("dim_product.product_key"), nullable=False
    )
    region_key = Column(
        Integer, ForeignKey("dim_region.region_key"), nullable=False
    )
    customer_key = Column(
        Integer, ForeignKey("dim_customer.customer_key"), nullable=False
    )
    revenue = Column(Numeric(12, 2), nullable=False)
    units = Column(Integer, nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
