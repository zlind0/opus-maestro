"""Scan/indexing management API."""

import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import ScanJob, User
from app.scanner import run_scan
from app.schemas import ScanStatus

router = APIRouter(prefix="/api/v1", tags=["scan"])

# Track the latest scan job
_latest_scan_id: uuid.UUID | None = None


@router.post("/scan")
async def trigger_scan(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
    mode: str = "incremental",
):
    global _latest_scan_id

    # Check if a scan is already running
    if _latest_scan_id:
        result = await db.execute(select(ScanJob).where(ScanJob.id == _latest_scan_id))
        existing = result.scalar_one_or_none()
        if existing and existing.status == "running":
            return {"message": "Scan already in progress", "scan_id": str(_latest_scan_id)}

    # Validate mode
    allowed = ("incremental", "with_unknowns", "full")
    if mode not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid scan mode: {mode}")

    job = ScanJob()
    # record requested mode in job.message for visibility
    job.message = mode
    db.add(job)
    await db.commit()
    await db.refresh(job)

    _latest_scan_id = job.id
    background_tasks.add_task(run_scan, job.id, mode)

    return {"message": "Scan started", "scan_id": str(job.id)}


@router.get("/scan/status", response_model=ScanStatus)
async def get_scan_status(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    global _latest_scan_id
    if not _latest_scan_id:
        return ScanStatus(status="idle", message="No scan has been run")

    result = await db.execute(select(ScanJob).where(ScanJob.id == _latest_scan_id))
    job = result.scalar_one_or_none()
    if not job:
        return ScanStatus(status="idle", message="No scan found")

    return ScanStatus(
        status=job.status,
        total=job.total_files or 0,
        current=job.processed_files or 0,
        message=job.message,
    )
