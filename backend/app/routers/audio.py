"""Audio streaming and playback API."""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audio import (
    get_output_content_type,
    requires_transcode,
    stream_audio_transcode,
    stream_native_file,
)
from app.auth import get_current_user
from app.database import get_db
from app.models import AudioFile, AudioSegment, User
from app.schemas import AudioSegmentOut

router = APIRouter(prefix="/api/v1/audio", tags=["audio"])


@router.get("/segments/{segment_id}")
async def stream_segment(
    segment_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Stream an audio segment. Native formats are served directly with range support;
    unsupported formats (APE) are transcoded to AAC on the fly."""
    result = await db.execute(
        select(AudioSegment).where(AudioSegment.id == segment_id)
    )
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(404, {"code": "RESOURCE_NOT_FOUND", "detail": "Audio segment not found"})

    result = await db.execute(
        select(AudioFile).where(AudioFile.id == segment.file_id)
    )
    audio_file = result.scalar_one_or_none()
    if not audio_file:
        raise HTTPException(404, {"code": "RESOURCE_NOT_FOUND", "detail": "Audio file not found"})

    file_path = audio_file.file_path
    content_type = get_output_content_type(file_path)

    # Duration in seconds for X-Content-Duration header
    duration_s: float | None = None
    if segment.end_time_ms is not None and segment.start_time_ms is not None:
        duration_s = (segment.end_time_ms - segment.start_time_ms) / 1000.0
    elif audio_file.duration_ms is not None:
        duration_s = audio_file.duration_ms / 1000.0

    if requires_transcode(file_path):
        # APE → fragmented AAC/MP4 stream (no byte-range support)
        headers = {
            "Cache-Control": "public, max-age=3600",
            "Accept-Ranges": "none",
        }
        if duration_s is not None:
            headers["X-Content-Duration"] = f"{duration_s:.3f}"
            headers["Content-Duration"] = f"{duration_s:.3f}"
        return StreamingResponse(
            stream_audio_transcode(file_path, segment.start_time_ms, segment.end_time_ms),
            media_type=content_type,
            headers=headers,
        )

    # Native file: serve with proper Content-Length and byte-range support
    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("Range")

    base_headers = {
        "Cache-Control": "public, max-age=3600",
        "Accept-Ranges": "bytes",
    }
    if duration_s is not None:
        base_headers["X-Content-Duration"] = f"{duration_s:.3f}"
        base_headers["Content-Duration"] = f"{duration_s:.3f}"

    if range_header:
        # Parse "bytes=start-end"
        try:
            range_val = range_header.replace("bytes=", "")
            parts = range_val.split("-")
            start_byte = int(parts[0]) if parts[0] else 0
            end_byte = int(parts[1]) if parts[1] else file_size - 1
        except (ValueError, IndexError):
            raise HTTPException(416, "Invalid Range header")

        end_byte = min(end_byte, file_size - 1)
        content_length = end_byte - start_byte + 1
        return StreamingResponse(
            stream_native_file(file_path, start_byte, end_byte),
            status_code=206,
            media_type=content_type,
            headers={
                **base_headers,
                "Content-Length": str(content_length),
                "Content-Range": f"bytes {start_byte}-{end_byte}/{file_size}",
            },
        )

    return StreamingResponse(
        stream_native_file(file_path, 0, None),
        media_type=content_type,
        headers={
            **base_headers,
            "Content-Length": str(file_size),
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
