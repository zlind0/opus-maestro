"""Music browsing and search API."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.llm import get_embedding
from app.models import Movement, User, Work
from app.schemas import MovementOut, SearchResult, WorkList, WorkOut, VersionOut
from app.models import Version

router = APIRouter(prefix="/api/v1", tags=["music"])


@router.get("/works", response_model=WorkList)
async def list_works(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    composer: str | None = None,
    era: str | None = None,
    work_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    stmt = select(Work)
    count_stmt = select(func.count()).select_from(Work)

    if composer:
        stmt = stmt.where(Work.composer.ilike(f"%{composer}%"))
        count_stmt = count_stmt.where(Work.composer.ilike(f"%{composer}%"))
    if era:
        stmt = stmt.where(Work.era == era)
        count_stmt = count_stmt.where(Work.era == era)
    if work_type:
        stmt = stmt.where(Work.work_type == work_type)
        count_stmt = count_stmt.where(Work.work_type == work_type)

    total = (await db.execute(count_stmt)).scalar() or 0
    result = await db.execute(stmt.order_by(Work.composer, Work.title).offset(offset).limit(limit))
    works = result.scalars().all()

    return WorkList(total=total, items=[WorkOut.model_validate(w) for w in works])


@router.get("/works/{work_id}", response_model=WorkOut)
async def get_work(
    work_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = await db.execute(select(Work).where(Work.id == work_id))
    work = result.scalar_one_or_none()
    if not work:
        raise HTTPException(404, {"code": "RESOURCE_NOT_FOUND", "detail": "Work not found"})
    return WorkOut.model_validate(work)


@router.get("/works/{work_id}/movements", response_model=list[MovementOut])
async def get_work_movements(
    work_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Movement).where(Movement.work_id == work_id).order_by(Movement.movement_number)
    )
    movements = result.scalars().all()
    return [MovementOut.model_validate(m) for m in movements]


@router.get("/works/{work_id}/versions", response_model=list[VersionOut])
async def get_work_versions(
    work_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Version).where(Version.work_id == work_id)
    )
    versions = result.scalars().all()
    return [VersionOut.model_validate(v) for v in versions]


@router.get("/search", response_model=SearchResult)
async def search(
    query: str | None = None,
    composer: str | None = None,
    era: str | None = None,
    work_type: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    # If structured filters provided, do precise search
    if composer or era or work_type:
        stmt = select(Work)
        if composer:
            stmt = stmt.where(Work.composer.ilike(f"%{composer}%"))
        if era:
            stmt = stmt.where(Work.era == era)
        if work_type:
            stmt = stmt.where(Work.work_type == work_type)
        result = await db.execute(stmt.limit(limit))
        works = result.scalars().all()
        return SearchResult(type="precise", results=[WorkOut.model_validate(w) for w in works])

    # Semantic search via embedding
    if query:
        embedding = await get_embedding(query)
        if embedding:
            # Find movements with similar embeddings, then get their works
            from pgvector.sqlalchemy import Vector

            result = await db.execute(
                select(Movement)
                .where(Movement.embedding.isnot(None))
                .order_by(Movement.embedding.cosine_distance(embedding))
                .limit(limit)
            )
            movements = result.scalars().all()
            work_ids = list({m.work_id for m in movements})

            if work_ids:
                result = await db.execute(select(Work).where(Work.id.in_(work_ids)))
                works = result.scalars().all()
                return SearchResult(type="semantic", results=[WorkOut.model_validate(w) for w in works])

        # Fallback: text search on canonical_string and title
        result = await db.execute(
            select(Work).where(
                or_(
                    Work.canonical_string.ilike(f"%{query}%"),
                    Work.title.ilike(f"%{query}%"),
                    Work.composer.ilike(f"%{query}%"),
                )
            ).limit(limit)
        )
        works = result.scalars().all()
        return SearchResult(type="precise", results=[WorkOut.model_validate(w) for w in works])

    # No query at all, return all
    result = await db.execute(select(Work).limit(limit))
    works = result.scalars().all()
    return SearchResult(type="precise", results=[WorkOut.model_validate(w) for w in works])
