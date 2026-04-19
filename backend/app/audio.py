"""Audio streaming via FFmpeg."""

import asyncio
import logging
import os
import shutil
from typing import AsyncGenerator, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Format mapping for FFmpeg output
FORMAT_MAP = {
    "mp3": {"codec": "libmp3lame", "content_type": "audio/mpeg", "ext": "mp3"},
    "flac": {"codec": "flac", "content_type": "audio/flac", "ext": "flac"},
    "m4a": {"codec": "aac", "content_type": "audio/mp4", "ext": "m4a"},
    "aac": {"codec": "aac", "content_type": "audio/mp4", "ext": "m4a"},
    "wav": {"codec": "pcm_s16le", "content_type": "audio/wav", "ext": "wav"},
}

# Formats that need conversion for browser playback
NEEDS_CONVERSION = {"ape", "alac"}


def get_ffmpeg_path() -> str:
    path = shutil.which("ffmpeg")
    if path is None:
        raise RuntimeError("ffmpeg not found in PATH")
    return path


def build_ffmpeg_command(
    file_path: str,
    target_format: str = "flac",
    start_ms: Optional[int] = None,
    end_ms: Optional[int] = None,
) -> list[str]:
    """Build FFmpeg command for audio streaming."""
    ffmpeg = get_ffmpeg_path()
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error"]

    # Seek to start position
    if start_ms and start_ms > 0:
        cmd.extend(["-ss", f"{start_ms / 1000:.3f}"])

    cmd.extend(["-i", file_path])

    # Duration (end - start)
    if end_ms is not None and end_ms > 0:
        start = start_ms or 0
        duration = (end_ms - start) / 1000
        cmd.extend(["-t", f"{duration:.3f}"])

    # Output format
    fmt = FORMAT_MAP.get(target_format, FORMAT_MAP["flac"])
    cmd.extend(["-acodec", fmt["codec"]])

    # Output to stdout
    cmd.extend(["-f", fmt["ext"], "pipe:1"])

    return cmd


def get_content_type(target_format: str) -> str:
    fmt = FORMAT_MAP.get(target_format, FORMAT_MAP["flac"])
    return fmt["content_type"]


def detect_source_format(file_path: str) -> str:
    """Detect format and determine if conversion is needed."""
    ext = os.path.splitext(file_path)[1].lstrip(".").lower()
    return ext


def needs_conversion(file_path: str, target_format: str) -> bool:
    """Check if the file needs transcoding."""
    src = detect_source_format(file_path)
    # APE always needs conversion
    if src == "ape":
        return True
    # ALAC (m4a with alac codec) needs conversion to flac
    if src == "m4a" and target_format == "flac":
        return True  # Will check codec later
    # Same format, no conversion needed (we still use ffmpeg for seeking)
    return src != target_format


async def stream_audio(
    file_path: str,
    target_format: str = "flac",
    start_ms: Optional[int] = None,
    end_ms: Optional[int] = None,
) -> AsyncGenerator[bytes, None]:
    """Stream audio through FFmpeg, yielding chunks."""
    cmd = build_ffmpeg_command(file_path, target_format, start_ms, end_ms)
    logger.info(f"FFmpeg command: {' '.join(cmd)}")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        while True:
            chunk = await process.stdout.read(65536)  # 64KB chunks
            if not chunk:
                break
            yield chunk
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()

        if process.returncode and process.returncode != 0:
            stderr = await process.stderr.read()
            logger.error(f"FFmpeg error: {stderr.decode()}")
