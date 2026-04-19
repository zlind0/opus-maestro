"""Recommendation API."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.llm import build_canonical_string, get_recommendations
from app.models import Movement, User, Work
from app.schemas import MovementOut, WorkOut

router = APIRouter(prefix="/api/v1", tags=["recommend"])


@router.get("/recommend/{movement_id}", response_model=list[WorkOut])
async def recommend(
    movement_id: uuid.UUID,
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get recommendations based on a movement."""
    result = await db.execute(
        select(Movement).where(Movement.id == movement_id)
    )
    movement = result.scalar_one_or_none()
    if not movement:
        raise HTTPException(404, {"code": "RESOURCE_NOT_FOUND", "detail": "Movement not found"})

    result = await db.execute(select(Work).where(Work.id == movement.work_id))
    work = result.scalar_one_or_none()
    if not work:
        raise HTTPException(404, {"code": "RESOURCE_NOT_FOUND", "detail": "Work not found"})

    # Try vector similarity first
    if movement.embedding is not None:
        result = await db.execute(
            select(Movement)
            .where(Movement.embedding.isnot(None))
            .where(Movement.work_id != work.id)
            .order_by(Movement.embedding.cosine_distance(movement.embedding))
            .limit(limit)
        )
        similar_movements = result.scalars().all()

        if similar_movements:
            work_ids = list({m.work_id for m in similar_movements})
            result = await db.execute(select(Work).where(Work.id.in_(work_ids)))
            works = result.scalars().all()
            if works:
                return [WorkOut.model_validate(w) for w in works[:limit]]

    # Fallback: LLM-based recommendations
    work_info = work.canonical_string or f"{work.composer} - {work.title}"
    llm_recs = await get_recommendations(work_info, limit)

    if llm_recs:
        # Try to match LLM recommendations to existing works in DB
        matched_works = []
        for rec in llm_recs:
            composer = rec.get("composer", "")
            title = rec.get("work_title", "")
            result = await db.execute(
                select(Work).where(
                    Work.composer.ilike(f"%{composer}%"),
                    Work.title.ilike(f"%{title}%"),
                ).limit(1)
            )
            w = result.scalar_one_or_none()
            if w:
                matched_works.append(WorkOut.model_validate(w))

        if matched_works:
            return matched_works[:limit]

    # Final fallback: same composer, different work
    result = await db.execute(
        select(Work).where(Work.composer == work.composer, Work.id != work.id).limit(limit)
    )
    works = result.scalars().all()
    return [WorkOut.model_validate(w) for w in works]
