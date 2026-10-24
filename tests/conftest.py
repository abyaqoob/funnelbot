"""Pytest fixtures for FunnelBot (Core Engine and API Integration)."""
from typing import Generator
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine
from app.api.deps import invalidate_faq_cache
from app.data.seed_loader import load_seed_data
from app.database import get_session
from app.engine.funnel_engine import FunnelEngine
from app.engine.llm_fallback import NoneLLMProvider
from app.engine.sql_storage import SQLStorage
from app.engine.storage import InMemoryStorage
from app.main import app


@pytest.fixture
def empty_storage() -> InMemoryStorage:
    """Returns a fresh empty in-memory storage."""
    return InMemoryStorage()


@pytest.fixture
def seeded_storage() -> InMemoryStorage:
    """Returns an in-memory storage loaded with default seed data."""
    storage = InMemoryStorage()
    load_seed_data(storage)
    return storage


@pytest.fixture
def engine(seeded_storage: InMemoryStorage) -> FunnelEngine:
    """Returns a FunnelEngine instance configured with seeded storage and no LLM."""
    return FunnelEngine(storage=seeded_storage, llm_provider=NoneLLMProvider())


@pytest.fixture
def test_db_session() -> Generator[Session, None, None]:
    """Provides an isolated in-memory SQLite session with StaticPool."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        storage = SQLStorage(session)
        load_seed_data(storage)
        session.commit()
        yield session


@pytest.fixture
def client(test_db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient wired to isolated in-memory test database."""

    def override_get_session():
        yield test_db_session

    app.dependency_overrides[get_session] = override_get_session
    # Invalidate cached FAQMatcher so it picks up the test db's FAQs
    storage = SQLStorage(test_db_session)
    invalidate_faq_cache(storage)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
