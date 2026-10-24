"""Pytest fixtures for FunnelBot."""
import pytest
from app.data.seed_loader import load_seed_data
from app.engine.funnel_engine import FunnelEngine
from app.engine.llm_fallback import NoneLLMProvider
from app.engine.storage import InMemoryStorage


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
