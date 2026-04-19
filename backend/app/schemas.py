import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Auth ──
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    username: str
    role: str

    model_config = {"from_attributes": True}


# ── Work ──
class WorkOut(BaseModel):
    id: uuid.UUID
    composer: str
    era: Optional[str] = None
    work_type: Optional[str] = None
    catalog_number: Optional[str] = None
    title: str
    movement_count: int = 0
    canonical_string: Optional[str] = None
    summary: Optional[str] = None

    model_config = {"from_attributes": True}


class WorkList(BaseModel):
    total: int
    items: list[WorkOut]


# ── Version ──
class VersionOut(BaseModel):
    id: uuid.UUID
    work_id: uuid.UUID
    conductor: Optional[str] = None
    ensemble: Optional[str] = None
    soloists: Optional[str] = None
    year: Optional[int] = None
    label: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Movement ──
class MovementOut(BaseModel):
    id: uuid.UUID
    work_id: uuid.UUID
    version_id: Optional[uuid.UUID] = None
    movement_number: int
    title: Optional[str] = None
    mood: Optional[str] = None
    description: Optional[str] = None

    model_config = {"from_attributes": True}


# ── AudioSegment ──
class AudioSegmentOut(BaseModel):
    id: uuid.UUID
    file_id: uuid.UUID
    movement_id: Optional[uuid.UUID] = None
    start_time_ms: int = 0
    end_time_ms: Optional[int] = None
    is_virtual: bool = False

    model_config = {"from_attributes": True}


# ── Search ──
class SearchResult(BaseModel):
    type: str  # "semantic" or "precise"
    results: list[WorkOut]


# ── Scan ──
class ScanStatus(BaseModel):
    status: str
    total: int = 0
    current: int = 0
    message: Optional[str] = None


# ── Health ──
class HealthResponse(BaseModel):
    status: str
    db: str
    llm: str


# ── Error ──
class ErrorResponse(BaseModel):
    code: str
    detail: str
