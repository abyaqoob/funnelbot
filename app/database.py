"""Database connection engine, session management, and initialization."""
import logging
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine, select

from app.config import settings
from app.data.seed_loader import load_seed_data
from app.models.db_models import (  # noqa: F401 - ensure models registered with metadata
    ConversationLogDB,
    ConversationStateDB,
    FAQItemDB,
    FlowDB,
    LeadDB,
    OptOutDB,
    RuleDB,
    RuleTriggerDB,
)

logger = logging.getLogger("funnelbot.db")

# SQLite needs check_same_thread=False for FastAPI concurrency
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding database session."""
    with Session(engine) as session:
        yield session


def init_db() -> None:
    """Create tables and seed initial data if empty."""
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables initialized successfully.")

    # Check if seed data needs to be populated
    from app.engine.sql_storage import SQLStorage

    with Session(engine) as session:
        existing_rules = session.exec(select(RuleDB)).first()
        if not existing_rules:
            logger.info("Database is empty. Loading default seed data...")
            storage = SQLStorage(session)
            counts = load_seed_data(storage)
            session.commit()
            logger.info("Seed data loaded successfully: %s", counts)
