import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")  # user / admin
    created_at = Column(DateTime, server_default=func.now())


class Work(Base):
    __tablename__ = "works"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    composer = Column(Text, nullable=False, index=True)
    era = Column(Text)  # 巴洛克, 古典, 浪漫, 现代 …
    work_type = Column(Text)  # 交响曲, 协奏曲, 奏鸣曲 …
    catalog_number = Column(Text)  # K.550, Op.67, BWV.232
    title = Column(Text, nullable=False)
    movement_count = Column(Integer, default=0)
    canonical_string = Column(Text)
    summary = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    versions = relationship("Version", back_populates="work", cascade="all, delete-orphan")
    movements = relationship("Movement", back_populates="work", cascade="all, delete-orphan",
                             order_by="Movement.movement_number")


class Version(Base):
    __tablename__ = "versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_id = Column(UUID(as_uuid=True), ForeignKey("works.id", ondelete="CASCADE"), nullable=False)
    conductor = Column(Text)
    ensemble = Column(Text)
    soloists = Column(Text)
    year = Column(Integer)
    label = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    work = relationship("Work", back_populates="versions")
    movements = relationship("Movement", back_populates="version", cascade="all, delete-orphan")


class Movement(Base):
    __tablename__ = "movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_id = Column(UUID(as_uuid=True), ForeignKey("works.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(UUID(as_uuid=True), ForeignKey("versions.id", ondelete="SET NULL"), nullable=True)
    movement_number = Column(Integer, nullable=False)
    title = Column(Text)
    mood = Column(String(50))  # joyful, melancholic, agitated, calm, mysterious, solemn, playful
    description = Column(Text)
    embedding = Column(Vector(1536))
    created_at = Column(DateTime, server_default=func.now())

    work = relationship("Work", back_populates="movements")
    version = relationship("Version", back_populates="movements")
    audio_segments = relationship("AudioSegment", back_populates="movement", cascade="all, delete-orphan")


class AudioFile(Base):
    __tablename__ = "audio_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_path = Column(Text, nullable=False, unique=True)
    file_format = Column(String(20))  # mp3, flac, m4a, ape, wav
    file_size = Column(Integer)
    duration_ms = Column(Integer)
    sample_rate = Column(Integer)
    bit_depth = Column(Integer)
    channels = Column(Integer)
    cue_path = Column(Text)  # associated CUE file path if any
    raw_tags = Column(Text)  # JSON of original ID3/Vorbis tags
    scanned_at = Column(DateTime, server_default=func.now())

    segments = relationship("AudioSegment", back_populates="audio_file", cascade="all, delete-orphan")


class AudioSegment(Base):
    __tablename__ = "audio_segments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey("audio_files.id", ondelete="CASCADE"), nullable=False)
    movement_id = Column(UUID(as_uuid=True), ForeignKey("movements.id", ondelete="SET NULL"), nullable=True)
    start_time_ms = Column(Integer, default=0)
    end_time_ms = Column(Integer)  # NULL = until end of file
    is_virtual = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    audio_file = relationship("AudioFile", back_populates="segments")
    movement = relationship("Movement", back_populates="audio_segments")


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
