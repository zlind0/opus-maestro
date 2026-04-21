"""Music library scanner — discovers audio files, extracts tags, calls LLM for metadata."""

import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import mutagen
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.apev2 import APEv2
from sqlalchemy import select, delete, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import async_session
from app.llm import build_canonical_string, extract_metadata, get_embedding
from app.models import AudioFile, AudioSegment, Movement, ScanJob, Version, Work

logger = logging.getLogger(__name__)
settings = get_settings()

SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ape", ".wav", ".wma", ".ogg", ".opus"}
CUE_EXTENSION = ".cue"


def extract_tags(file_path: str) -> dict:
    """Extract metadata tags from audio file using mutagen."""
    tags = {"file_path": file_path, "file_name": os.path.basename(file_path)}
    try:
        audio = mutagen.File(file_path, easy=True)
        if audio is None:
            return tags

        tags["duration_ms"] = int((audio.info.length or 0) * 1000)
        tags["sample_rate"] = getattr(audio.info, "sample_rate", None)
        tags["channels"] = getattr(audio.info, "channels", None)
        tags["bit_depth"] = getattr(audio.info, "bits_per_sample", None)

        # Extract common tags
        tag_keys = ["title", "artist", "album", "albumartist", "composer",
                     "genre", "date", "tracknumber", "discnumber", "performer",
                     "conductor", "ensemble", "organization", "label"]
        for key in tag_keys:
            val = audio.get(key)
            if val:
                tags[key] = val[0] if isinstance(val, list) else str(val)
    except Exception as e:
        logger.warning(f"Tag extraction failed for {file_path}: {e}")

    return tags


def _sanitize_composer(val: Optional[str]) -> str:
    """Return a safe composer string; use '其他' when missing or empty.

    Treat common placeholders like 'Unknown' or empty strings as missing.
    """
    if val is None:
        return "其他"
    try:
        s = str(val).strip()
    except Exception:
        return "其他"
    if not s:
        return "其他"
    lowered = s.lower()
    if lowered in ("unknown", "unknown work", "unk", "other", "n/a", "none"):
        return "其他"
    return s


def parse_cue_file(cue_path: str) -> list[dict]:
    """Parse a CUE file and return track information.
    
    Returns list of dicts with keys: track_number, title, performer, start_time_ms
    """
    tracks = []
    current_track = {}

    try:
        # Try multiple encodings
        content = None
        for encoding in ["utf-8-sig", "utf-8", "gbk", "gb2312", "shift_jis", "latin-1"]:
            try:
                with open(cue_path, "r", encoding=encoding) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if content is None:
            logger.error(f"Cannot decode CUE file: {cue_path}")
            return []

        for line in content.splitlines():
            line = line.strip()

            track_match = re.match(r'TRACK\s+(\d+)\s+AUDIO', line)
            if track_match:
                if current_track:
                    tracks.append(current_track)
                current_track = {"track_number": int(track_match.group(1))}
                continue

            title_match = re.match(r'TITLE\s+"(.+)"', line)
            if title_match and current_track:
                current_track["title"] = title_match.group(1)
                continue

            performer_match = re.match(r'PERFORMER\s+"(.+)"', line)
            if performer_match and current_track:
                current_track["performer"] = performer_match.group(1)
                continue

            index_match = re.match(r'INDEX\s+01\s+(\d+):(\d+):(\d+)', line)
            if index_match and current_track:
                minutes = int(index_match.group(1))
                seconds = int(index_match.group(2))
                frames = int(index_match.group(3))
                current_track["start_time_ms"] = (minutes * 60 + seconds) * 1000 + int(frames / 75 * 1000)
                continue

        if current_track:
            tracks.append(current_track)

    except Exception as e:
        logger.error(f"CUE parsing failed for {cue_path}: {e}")

    return tracks


def find_audio_files(root_path: str) -> list[str]:
    """Recursively find all supported audio files."""
    files = []
    for dirpath, _, filenames in os.walk(root_path):
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                files.append(os.path.join(dirpath, fname))
    return sorted(files)


def find_cue_for_audio(audio_path: str) -> Optional[str]:
    """Find associated CUE file for an audio file."""
    base = os.path.splitext(audio_path)[0]
    cue_path = base + ".cue"
    if os.path.exists(cue_path):
        return cue_path

    # Check same directory for any CUE file
    directory = os.path.dirname(audio_path)
    for f in os.listdir(directory):
        if f.lower().endswith(".cue"):
            return os.path.join(directory, f)
    return None


async def find_or_create_work(
    db: AsyncSession, metadata: dict
) -> Work:
    """Find existing work or create new one based on extracted metadata."""
    composer = _sanitize_composer(metadata.get("composer") or metadata.get("artist"))
    catalog_number = metadata.get("catalog_number")

    # Try to find by composer + catalog number
    if catalog_number:
        result = await db.execute(
            select(Work).where(
                Work.composer == composer,
                Work.catalog_number == catalog_number,
            )
        )
        work = result.scalar_one_or_none()
        if work:
            return work

    # Try to find by composer + title
    title = metadata.get("work_title", "Unknown Work")
    result = await db.execute(
        select(Work).where(
            Work.composer == composer,
            Work.title == title,
        )
    )
    work = result.scalar_one_or_none()
    if work:
        return work

    # Create new work
    canonical = build_canonical_string(metadata)
    work = Work(
        composer=composer,
        era=metadata.get("era"),
        work_type=metadata.get("work_type"),
        catalog_number=catalog_number,
        title=title,
        movement_count=0,
        canonical_string=canonical,
        summary=metadata.get("work_summary"),
    )
    db.add(work)
    await db.flush()
    return work


async def find_or_create_version(
    db: AsyncSession, work: Work, metadata: dict
) -> Version:
    """Find existing version or create new one."""
    conductor = metadata.get("conductor")
    ensemble = metadata.get("ensemble")
    year = metadata.get("year")

    if conductor or ensemble:
        stmt = select(Version).where(Version.work_id == work.id)
        if conductor:
            stmt = stmt.where(Version.conductor == conductor)
        if ensemble:
            stmt = stmt.where(Version.ensemble == ensemble)
        result = await db.execute(stmt)
        version = result.scalar_one_or_none()
        if version:
            return version

    version = Version(
        work_id=work.id,
        conductor=conductor,
        ensemble=ensemble,
        soloists=metadata.get("soloists"),
        year=year,
        label=metadata.get("label"),
    )
    db.add(version)
    await db.flush()
    return version


async def process_single_file(
    db: AsyncSession, file_path: str, language: str = "简体中文", force: bool = False
) -> Optional[AudioFile]:
    """Process a single audio file: extract tags, call LLM, create DB records.

    If `force` is True, any existing `AudioFile` entry for `file_path` will be
    removed before reprocessing (useful when re-scanning files marked as
    unknown work or for a full reindex).
    """
    # Check if already scanned (unless force requested)
    existing = None
    result = await db.execute(select(AudioFile).where(AudioFile.file_path == file_path))
    existing = result.scalar_one_or_none()
    if existing and not force:
        logger.info(f"Skipping already scanned file: {file_path}")
        return None

    # If force is requested and an existing record exists, delete it so we
    # create fresh records for this file. Also remove any Movements that
    # become orphaned after removing the file's AudioSegments, and update
    # the parent Work's movement_count accordingly. This prevents stale
    # "Unknown Work" records from accumulating.
    if existing and force:
        try:
            # collect affected movement ids and their work ids before deletion
            try:
                rows = await db.execute(
                    select(AudioSegment.movement_id, Movement.work_id)
                    .join(Movement, AudioSegment.movement_id == Movement.id)
                    .where(AudioSegment.file_id == existing.id)
                )
                pairs = rows.all() or []
            except Exception:
                pairs = []

            movement_ids = {m for m, _ in pairs if m}
            work_ids = {w for _, w in pairs if w}

            await db.execute(delete(AudioFile).where(AudioFile.id == existing.id))
            await db.flush()

            # For each movement previously associated with this file, if it
            # has no remaining audio segments, delete it.
            for mov_id in movement_ids:
                try:
                    seg_check = await db.execute(select(AudioSegment.id).where(AudioSegment.movement_id == mov_id).limit(1))
                    if seg_check.scalar_one_or_none() is None:
                        await db.execute(delete(Movement).where(Movement.id == mov_id))
                except Exception:
                    logger.warning(f"Failed to cleanup Movement {mov_id} after reprocessing {file_path}")

            # Update movement_count for affected works and remove entirely
            # empty 'Unknown Work' entries for cleanliness.
            for work_id in work_ids:
                try:
                    cnt_res = await db.execute(select(func.count()).select_from(Movement).where(Movement.work_id == work_id))
                    cnt = cnt_res.scalar_one() or 0
                    await db.execute(
                        select(Work).where(Work.id == work_id)
                    )
                    # Update movement_count via ORM-friendly update
                    await db.execute(
                        # Use SQLAlchemy core update via delete().where() isn't suitable; use simple UPDATE through text-expression
                        # But to keep it simple here, load the Work and set attribute
                        select(Work).where(Work.id == work_id)
                    )
                    # Fetch work and set movement_count if present
                    work_obj_res = await db.execute(select(Work).where(Work.id == work_id))
                    work_obj = work_obj_res.scalar_one_or_none()
                    if work_obj:
                        work_obj.movement_count = int(cnt)
                        # If this is an 'Unknown Work' and now has no movements and
                        # no versions, delete the Work record to avoid clutter.
                        if work_obj.movement_count == 0 and getattr(work_obj, 'title', None) == "Unknown Work":
                            try:
                                ver_check = await db.execute(select(Version.id).where(Version.work_id == work_id).limit(1))
                                if ver_check.scalar_one_or_none() is None:
                                    await db.execute(delete(Work).where(Work.id == work_id))
                            except Exception:
                                logger.warning(f"Failed to delete empty Unknown Work {work_id}")
                except Exception:
                    logger.warning(f"Failed to update movement_count for Work {work_id}")

            await db.flush()
        except Exception:
            # If deletion fails, proceed but log a warning
            logger.warning(f"Failed to delete existing AudioFile before reprocessing: {file_path}")

    # Extract tags
    tags = extract_tags(file_path)
    file_format = os.path.splitext(file_path)[1].lstrip(".").lower()

    # Create AudioFile record
    audio_file = AudioFile(
        file_path=file_path,
        file_format=file_format,
        file_size=os.path.getsize(file_path),
        duration_ms=tags.get("duration_ms"),
        sample_rate=tags.get("sample_rate"),
        bit_depth=tags.get("bit_depth"),
        channels=tags.get("channels"),
        raw_tags=json.dumps(tags, ensure_ascii=False),
    )

    # Check for CUE file
    cue_path = find_cue_for_audio(file_path)
    if cue_path:
        audio_file.cue_path = cue_path

    db.add(audio_file)
    await db.flush()

    # Extract metadata via LLM
    metadata = await extract_metadata(file_path, tags, language)
    if metadata is None:
        # Fallback: create basic records from tags
        metadata = {
            "composer": _sanitize_composer(tags.get("composer") or tags.get("artist")),
            "work_title": tags.get("album") or tags.get("title") or "Unknown Work",
            "era": None,
            "work_type": None,
            "catalog_number": None,
            "movement_title": tags.get("title"),
            "movement_number": _parse_track_number(tags.get("tracknumber")),
            "mood": None,
            "conductor": tags.get("conductor"),
            "ensemble": tags.get("ensemble"),
            "soloists": tags.get("performer"),
            "year": _parse_year(tags.get("date")),
            "label": tags.get("label") or tags.get("organization"),
        }

    # Create Work, Version, Movement
    work = await find_or_create_work(db, metadata)
    version = await find_or_create_version(db, work, metadata)

    if cue_path:
        # CUE file: create virtual segments for each track
        cue_tracks = parse_cue_file(cue_path)
        for i, track in enumerate(cue_tracks):
            end_time = cue_tracks[i + 1]["start_time_ms"] if i + 1 < len(cue_tracks) else None

            movement = Movement(
                work_id=work.id,
                version_id=version.id,
                movement_number=track.get("track_number", i + 1),
                title=track.get("title", metadata.get("movement_title")),
                mood=metadata.get("mood"),
                description=metadata.get("description"),
            )
            db.add(movement)
            await db.flush()

            segment = AudioSegment(
                file_id=audio_file.id,
                movement_id=movement.id,
                start_time_ms=track["start_time_ms"],
                end_time_ms=end_time,
                is_virtual=True,
            )
            db.add(segment)

        work.movement_count = max(work.movement_count or 0, len(cue_tracks))
    else:
        # Single file: one segment = one movement
        mv_number = metadata.get("movement_number") or 1
        movement = Movement(
            work_id=work.id,
            version_id=version.id,
            movement_number=mv_number,
            title=metadata.get("movement_title"),
            mood=metadata.get("mood"),
            description=metadata.get("description"),
        )
        db.add(movement)
        await db.flush()

        segment = AudioSegment(
            file_id=audio_file.id,
            movement_id=movement.id,
            start_time_ms=0,
            end_time_ms=None,
            is_virtual=False,
        )
        db.add(segment)

        work.movement_count = max(work.movement_count or 0, mv_number)

    # Generate embedding for the canonical string (if enabled)
    canonical = build_canonical_string(metadata)
    if canonical and getattr(settings, "enable_embeddings", True):
        embedding = await get_embedding(canonical)
        if embedding and movement:
            movement.embedding = embedding

    await db.flush()
    return audio_file


def _parse_track_number(val) -> int:
    if val is None:
        return 1
    try:
        return int(str(val).split("/")[0])
    except (ValueError, IndexError):
        return 1


def _parse_year(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(str(val)[:4])
    except (ValueError, IndexError):
        return None


async def run_scan(scan_job_id: uuid.UUID, mode: str = "incremental"):
    """Background task: scan music library and index files.

    Supports three modes:
      - "incremental": only process newly discovered files
      - "with_unknowns": process new files and reprocess files linked to
        works titled "Unknown Work"
      - "full": delete existing `AudioFile` entries and reprocess all files

    In all modes, any DB entries pointing to files that no longer exist on
    disk are removed before indexing.
    """
    async with async_session() as db:
        try:
            result = await db.execute(select(ScanJob).where(ScanJob.id == scan_job_id))
            job = result.scalar_one()
            job.status = "running"
            job.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.commit()

            music_path = settings.music_path
            files = find_audio_files(music_path)
            job.total_files = len(files)
            await db.commit()

            # Remove DB entries for files that no longer exist on disk
            db_paths_result = await db.execute(select(AudioFile.file_path))
            db_paths = set(db_paths_result.scalars().all())
            files_set = set(files)
            missing = db_paths - files_set
            if missing:
                for path in missing:
                    try:
                        await db.execute(delete(AudioFile).where(AudioFile.file_path == path))
                    except Exception as e:
                        logger.warning(f"Failed to delete missing audio file record {path}: {e}")
                await db.commit()

            # If full re-scan requested, clear all existing AudioFile entries so
            # every file will be processed from scratch.
            # Validate/normalize mode. Prefer explicit function argument; fall back
            # to job.message if the provided mode is not valid.
            allowed_modes = ("incremental", "with_unknowns", "full")
            if not isinstance(mode, str) or mode not in allowed_modes:
                if isinstance(job.message, str) and job.message in allowed_modes:
                    mode = job.message
                else:
                    mode = "incremental"

            # If full, clear all audio-related tables so the database is
            # rebuilt from scratch during the scan. Delete in dependency
            # order to avoid FK constraint issues and avoid relying on DB
            #-level ON DELETE behavior.
            if mode == "full":
                try:
                    await db.execute(delete(AudioSegment))
                    await db.execute(delete(AudioFile))
                    await db.execute(delete(Movement))
                    await db.execute(delete(Version))
                    await db.execute(delete(Work))
                    await db.commit()
                except Exception as e:
                    logger.warning(f"Failed to clear audio-related tables for full scan: {e}")
                    await db.rollback()

            # For 'with_unknowns' mode, pre-compute paths that should be reprocessed
            unknown_paths = set()
            if mode == "with_unknowns":
                try:
                    stmt = select(AudioFile.file_path).join(AudioFile.segments).join(AudioSegment.movement).join(Movement.work).where(
                        or_(Work.title == "Unknown Work", Work.composer == "其他")
                    )
                    res = await db.execute(stmt)
                    unknown_paths = set(res.scalars().all())
                except Exception as e:
                    logger.warning(f"Failed to compute unknown work paths: {e}")

            for i, file_path in enumerate(files):
                try:
                    if mode == "incremental":
                        await process_single_file(db, file_path, settings.default_language, force=False)
                    elif mode == "with_unknowns":
                        if file_path in unknown_paths:
                            await process_single_file(db, file_path, settings.default_language, force=True)
                        else:
                            await process_single_file(db, file_path, settings.default_language, force=False)
                    elif mode == "full":
                        # all AudioFile entries removed earlier, so treat as fresh
                        await process_single_file(db, file_path, settings.default_language, force=False)
                    else:
                        # fallback to incremental behavior
                        await process_single_file(db, file_path, settings.default_language, force=False)

                    await db.commit()
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    await db.rollback()

                job.processed_files = i + 1
                job.message = f"Processing: {os.path.basename(file_path)}"
                await db.commit()

            job.status = "completed"
            job.message = f"Scan complete: {len(files)} files processed ({mode})"
            job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.commit()

        except Exception as e:
            logger.error(f"Scan job failed: {e}")
            try:
                job.status = "failed"
                job.message = str(e)
                await db.commit()
            except Exception:
                pass
