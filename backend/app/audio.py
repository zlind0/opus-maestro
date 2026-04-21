"""Audio streaming via FFmpeg."""

import asyncio
import logging
import os
import shutil
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)

# Formats that browsers cannot play natively and must be transcoded to AAC
TRANSCODE_TO_AAC = {"ape"}

# Content-type map for native browser-playable formats
NATIVE_CONTENT_TYPES = {
    "mp3": "audio/mpeg",
    "flac": "audio/flac",
    "m4a": "audio/mp4",
    "aac": "audio/mp4",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "opus": "audio/ogg",
}


def get_ffmpeg_path() -> str:
    path = shutil.which("ffmpeg")
    if path is None:
        raise RuntimeError("ffmpeg not found in PATH")
    return path


def get_source_ext(file_path: str) -> str:
    return os.path.splitext(file_path)[1].lstrip(".").lower()


def requires_transcode(file_path: str) -> bool:
    return get_source_ext(file_path) in TRANSCODE_TO_AAC


def get_output_content_type(file_path: str) -> str:
    """Return the content-type that will actually be served for this file."""
    if requires_transcode(file_path):
        return "audio/mp4"  # AAC in MP4 container
    ext = get_source_ext(file_path)
    return NATIVE_CONTENT_TYPES.get(ext, "audio/flac")


async def stream_audio_transcode(
    file_path: str,
    start_ms: Optional[int] = None,
    end_ms: Optional[int] = None,
) -> AsyncGenerator[bytes, None]:
    """Transcode APE (and other unsupported formats) to AAC/MP4 and stream."""
    ffmpeg = get_ffmpeg_path()
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error"]

    if start_ms and start_ms > 0:
        cmd.extend(["-ss", f"{start_ms / 1000:.3f}"])

    cmd.extend(["-i", file_path])

    if end_ms is not None and end_ms > 0:
        start = start_ms or 0
        duration_s = (end_ms - start) / 1000
        cmd.extend(["-t", f"{duration_s:.3f}"])

    # AAC in fragmented MP4 — fragmented so it can be streamed without a seekable file
    cmd.extend(["-acodec", "aac", "-f", "mp4", "-movflags", "frag_keyframe+empty_moov", "pipe:1"])

    logger.info(f"FFmpeg transcode command: {' '.join(cmd)}")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        while True:
            chunk = await process.stdout.read(65536)
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


async def stream_native_file(
    file_path: str,
    start_byte: int = 0,
    end_byte: Optional[int] = None,
) -> AsyncGenerator[bytes, None]:
    """Stream a native file directly, supporting byte-range reads."""
    chunk_size = 65536
    async with asyncio.timeout(300):
        with open(file_path, "rb") as f:
            f.seek(start_byte)
            remaining = (end_byte - start_byte + 1) if end_byte is not None else None
            while True:
                to_read = chunk_size if remaining is None else min(chunk_size, remaining)
                chunk = f.read(to_read)
                if not chunk:
                    break
                yield chunk
                if remaining is not None:
                    remaining -= len(chunk)
                    if remaining <= 0:
                        break
