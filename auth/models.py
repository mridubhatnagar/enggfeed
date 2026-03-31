import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class User(Base):
    __tablename__ = "user"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_auth_id = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    email = Column(Text, nullable=False)
    profile_url = Column(Text, nullable=False)


class AllowedUser(Base):
    __tablename__ = "allowed_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, nullable=False)
