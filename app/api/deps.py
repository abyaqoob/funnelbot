"""API dependencies: Database sessions, storage, engine, and admin security."""
import secrets

from fastapi import Depends, Header, HTTPException, Query, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlmodel import Session

from app.config import settings
from app.database import get_session
from app.engine.faq_matcher import FAQMatcher
from app.engine.funnel_engine import FunnelEngine
from app.engine.llm_fallback import get_llm_provider
from app.engine.sql_storage import SQLStorage
from app.engine.storage import Storage

security_basic = HTTPBasic(auto_error=False)

# Global cached FAQMatcher to optimize TF-IDF across requests
_cached_faq_matcher: FAQMatcher | None = None


def get_db_storage(session: Session = Depends(get_session)) -> Storage:
    """Dependency returning database-backed storage."""
    return SQLStorage(session)


def get_cached_faq_matcher(storage: Storage) -> FAQMatcher:
    """Returns cached FAQMatcher, initializing if not present."""
    global _cached_faq_matcher
    if _cached_faq_matcher is None:
        _cached_faq_matcher = FAQMatcher(storage.get_faqs())
    return _cached_faq_matcher


def invalidate_faq_cache(storage: Storage) -> None:
    """Invalidate and re-fit FAQMatcher after FAQ edits."""
    global _cached_faq_matcher
    _cached_faq_matcher = FAQMatcher(storage.get_faqs())


def get_funnel_engine(storage: Storage = Depends(get_db_storage)) -> FunnelEngine:
    """Dependency injecting configured FunnelEngine instance."""
    engine = FunnelEngine(storage=storage, llm_provider=get_llm_provider())
    # Reuse cached FAQMatcher
    engine.faq_matcher = get_cached_faq_matcher(storage)
    return engine


def verify_admin_access(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(security_basic),
    x_admin_password: str | None = Header(None, alias="X-Admin-Password"),
    token: str | None = Query(None),
) -> bool:
    """
    Validates admin authorization.
    In DEMO_MODE:
      - GET requests are publicly accessible (read-only demo mode).
      - Mutations (POST/PUT/DELETE) require valid admin password.
    In PRODUCTION / DEMO_MODE=False:
      - All routes require valid admin password.
    """
    provided_password = None

    if x_admin_password:
        provided_password = x_admin_password
    elif credentials and credentials.password:
        provided_password = credentials.password
    elif token:
        provided_password = token

    is_authenticated = False
    if provided_password and secrets.compare_digest(provided_password, settings.ADMIN_PASSWORD):
        is_authenticated = True

    if is_authenticated:
        return True

    # Read-only public demo access
    if settings.DEMO_MODE and request.method == "GET":
        return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Admin authentication required. Mutations are restricted in demo mode.",
        headers={"WWW-Authenticate": "Basic"},
    )
