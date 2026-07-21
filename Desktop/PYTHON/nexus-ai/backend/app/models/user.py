import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.db.postgres import Base

class Role(str, enum.Enum):
    admin = "admin"
    analyst = "analyst"
    viewer = "viewer"

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(Role), default=Role.viewer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
