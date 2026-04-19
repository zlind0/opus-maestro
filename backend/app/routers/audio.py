"""Audio streaming and playback API."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audio import get_content_type, stream_audio
from app.auth import get_current_user
from app.database import get_db
from app.models import AudioFile, AudioSegment, Movement, User, Work
from app.schemas import AudioSegmentOut, MovementOut

router = APIRouter(prefix="/api/v1/audio", tags=["audio"])


@router.get("/segments/{segment_id}")
async def stream_segment(
    segment_id: uuid.UUID,
    target_format: str = Query("flac", regex="^(flac|mp3|m4a|wav)$"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Stream an audio segment, optionally converting format."""
    result = await db.execute(
        select(AudioSegment).where(AudioSegment.id == segment_id)
    )
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(404, {"code": "RESOURCE_NOT_FOUND", "detail": "Audio segment not found"})

    # Get the audio file
    result = await db.execute(
        select(AudioFile).where(AudioFile.id == segment.file_id)
    )
    audio_file = result.scalar_one_or_none()
    if not audio_file:
        raise HTTPException(404, {"code": "RESOURCE_NOT_FOUND", "detail": "Audio file not found"})

    content_type = get_content_type(target_format)

    return StreamingResponse(
        stream_audio(
            file_path=audio_file.file_path,
            target_format=target_format,
            start_ms=segment.start_time_ms,
            end_ms=segment.end_time_ms,
        ),
        media_type=content_type,
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": f"public, max-age={3600}",
        },
    )


@router.get("/movements/{movement_id}/segments", response_model=list[AudioSegmentOut])
async def get_movement_segments(
    movement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get audio segments for a movement."""
    result = await db.execute(
        select(AudioSegment).where(AudioSegment.movement_id == movement_id)
    )
    segments = result.scalars().all()
    return [AudioSegmentOut.model_validate(s) for s in segments]
