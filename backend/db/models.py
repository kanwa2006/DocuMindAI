from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base
import datetime


class User(Base):
    __tablename__ = "users"
    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String, unique=True, index=True, nullable=False)
    email           = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at      = Column(DateTime, default=datetime.datetime.utcnow)
    documents       = relationship("Document",    back_populates="owner",   cascade="all, delete")
    chats           = relationship("ChatHistory", back_populates="owner",   cascade="all, delete")
    sessions        = relationship("ChatSession", back_populates="owner",   cascade="all, delete")


class Document(Base):
    __tablename__ = "documents"
    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename      = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    uploaded_at   = Column(DateTime, default=datetime.datetime.utcnow)
    page_count    = Column(Integer, default=0)
    is_indexed    = Column(Integer, default=0)  # 0=pending, 1=done, 2=failed
    owner         = relationship("User", back_populates="documents")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False)
    title          = Column(String(200), default="New Chat")
    doc_ids        = Column(Text, default="[]")  # JSON list of doc IDs uploaded in this session
    created_at     = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.datetime.utcnow)
    owner          = relationship("User", back_populates="sessions")
    messages       = relationship("ChatHistory", back_populates="session", cascade="all, delete")


class ChatHistory(Base):
    __tablename__ = "chat_history"
    __table_args__ = {"extend_existing": True}
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True)
    question   = Column(Text, nullable=False)
    answer     = Column(Text, nullable=False)
    sources    = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    owner      = relationship("User", back_populates="chats")
    session    = relationship("ChatSession", back_populates="messages")
