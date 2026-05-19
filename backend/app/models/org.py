import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, func, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class Organization(Base):
    __tablename__ = "organizations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# FIX 0.6: Added workspace_id column and roles relationship that auth.py requires
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    # FIX 0.6: workspace_id — the user's active workspace (defaults to general)
    workspace_id = Column(String(50), nullable=True, default="general")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Phase 10 — trial / billing plan
    plan = Column(String(50), nullable=False, default="trial")
    trial_queries_used = Column(Integer, nullable=False, default=0)
    trial_started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    subscribed_at = Column(DateTime, nullable=True)
    subscription_ends_at = Column(DateTime, nullable=True)

    # Phase 10 — email verification
    email_verified = Column(Boolean, nullable=False, default=False)

    # FIX 0.6: roles relationship — auth.py reads [r.role for r in user.roles]
    roles = relationship(
        "UserRole",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan"
    )


# FIX 0.6: UserRole model — auth.py iterates user.roles expecting .role attribute
class UserRole(Base):
    __tablename__ = "user_roles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role = Column(String(50), nullable=False, default="user")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="roles")


class OrganizationUser(Base):
    __tablename__ = "organization_users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    role = Column(String, nullable=False, default="viewer")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
