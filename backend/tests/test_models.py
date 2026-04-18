"""Tests for database models."""

import uuid
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AudioFile, Work, Movement, User, AudioSegment


@pytest.mark.asyncio
async def test_create_audio_file(async_session: AsyncSession):
    """Test creating an audio file record."""
    audio_file = AudioFile(
        id=str(uuid.uuid4()),
        path='/data/audio/test.flac',
        filename='test.flac',
        mime_type='audio/flac',
        duration_ms=180000,
        size_bytes=50000000,
    )
    async_session.add(audio_file)
    await async_session.commit()
    await async_session.refresh(audio_file)
    
    assert audio_file.id is not None
    assert audio_file.path == '/data/audio/test.flac'
    assert audio_file.duration_ms == 180000


@pytest.mark.asyncio
async def test_create_work(async_session: AsyncSession):
    """Test creating a work/composition record."""
    work = Work(
        work_id=str(uuid.uuid4()),
        composer='Wolfgang Amadeus Mozart',
        era='Classical',
        work_type='Symphony',
        catalog_number='K. 550',
        title='Symphony No. 40 in G minor',
        movement_count=4,
        canonical_string='Composer: Mozart | Title: Symphony No. 40 | Era: Classical',
        language='zh-CN',
    )
    async_session.add(work)
    await async_session.commit()
    await async_session.refresh(work)
    
    assert work.work_id is not None
    assert work.composer == 'Wolfgang Amadeus Mozart'
    assert work.title == 'Symphony No. 40 in G minor'


@pytest.mark.asyncio
async def test_create_movement(async_session: AsyncSession):
    """Test creating a movement record."""
    # First create a work
    work = Work(
        work_id=str(uuid.uuid4()),
        composer='Ludwig van Beethoven',
        title='Symphony No. 5',
        language='zh-CN',
    )
    async_session.add(work)
    await async_session.commit()
    
    # Then create a movement
    movement = Movement(
        movement_id=str(uuid.uuid4()),
        work_id=work.work_id,
        movement_number=1,
        movement_title='Allegro con brio',
        emotion='Angry/Fierce',
        description='Dramatic opening with famous motif',
    )
    async_session.add(movement)
    await async_session.commit()
    await async_session.refresh(movement)
    
    assert movement.movement_id is not None
    assert movement.work_id == work.work_id
    assert movement.movement_number == 1


@pytest.mark.asyncio
async def test_create_user(async_session: AsyncSession):
    """Test creating a user record."""
    from app.utils import get_password_hash
    
    user = User(
        id=str(uuid.uuid4()),
        username='testuser',
        email='test@example.com',
        hashed_password=get_password_hash('password123'),
        role='listener',
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    assert user.id is not None
    assert user.username == 'testuser'
    assert user.role == 'listener'


@pytest.mark.asyncio
async def test_audio_file_segments_relationship(async_session: AsyncSession):
    """Test relationship between audio files and segments."""
    # Create audio file
    audio_file = AudioFile(
        id=str(uuid.uuid4()),
        path='/data/audio/test.flac',
        filename='test.flac',
    )
    async_session.add(audio_file)
    await async_session.commit()
    
    # Create segments
    segment1 = AudioSegment(
        id=str(uuid.uuid4()),
        file_id=audio_file.id,
        start_time_ms=0,
        end_time_ms=60000,
        title='Movement I',
    )
    segment2 = AudioSegment(
        id=str(uuid.uuid4()),
        file_id=audio_file.id,
        start_time_ms=60000,
        end_time_ms=120000,
        title='Movement II',
    )
    async_session.add_all([segment1, segment2])
    await async_session.commit()
    
    # Refresh and check relationship
    await async_session.refresh(audio_file)
    assert len(audio_file.segments) == 2
    assert audio_file.segments[0].title == 'Movement I'
