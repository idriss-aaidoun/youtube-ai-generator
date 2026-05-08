"""
Base de données SQLite via SQLAlchemy
Table video_jobs : historique de chaque génération
"""
import os
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///db/videos.db")

os.makedirs("db", exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class VideoJob(Base):
    __tablename__ = "video_jobs"

    id                 = Column(Integer, primary_key=True, index=True)
    job_id             = Column(String(36), unique=True, index=True, nullable=False)
    subject            = Column(Text, nullable=False)
    style              = Column(String(50), nullable=False)
    duration           = Column(String(20), nullable=False)
    voice              = Column(String(20), nullable=False)
    language           = Column(String(20), nullable=False)
    status             = Column(String(20), default="pending")
    progress           = Column(Integer, default=0)
    current_step       = Column(String(200), default="")
    script_title       = Column(Text, nullable=True)
    script_description = Column(Text, nullable=True)
    script_json        = Column(Text, nullable=True)
    video_path         = Column(Text, nullable=True)
    thumbnail_path     = Column(Text, nullable=True)
    subtitle_path      = Column(Text, nullable=True)
    error_message      = Column(Text, nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)
    completed_at       = Column(DateTime, nullable=True)


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
