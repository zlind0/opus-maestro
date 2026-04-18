import os
import sys
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.models import Base
from app.database import get_db


@pytest.fixture
async def async_session():
    """Create a test database session."""
    # Use SQLite for testing (in-memory)
    engine = create_async_engine('sqlite+aiosqlite:///:memory:', echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with TestingSessionLocal() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def test_audio_dir():
    """Get the testdata audio directory."""
    return Path(__file__).parent.parent.parent / 'testdata' / 'audio'


@pytest.fixture
def test_audio_files(test_audio_dir):
    """Get list of test audio files."""
    if not test_audio_dir.exists():
        return []
    return sorted(test_audio_dir.glob('*.m4a'))
