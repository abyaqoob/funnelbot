"""Admin management endpoints: Rules, FAQs, Flows, Leads, Logs, and Analytics."""
import csv
import io
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlmodel import Session, col, func, select
from app.api.deps import get_db_storage, invalidate_faq_cache, verify_admin_access
from app.database import get_session
from app.engine.storage import Storage
from app.models.db_models import (
    ConversationLogDB,
    ConversationStateDB,
    LeadDB,
)
from app.models.faq import FAQItem
from app.models.flow import QualificationFlow
from app.models.leads import Lead
from app.models.rules import TriggerRule

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
    dependencies=[Depends(verify_admin_access)],
)


# ==========================================
# RULES
# ==========================================

@router.get("/rules", response_model=List[TriggerRule])
def list_rules(storage: Storage = Depends(get_db_storage)):
    """List all trigger rules."""
    return storage.get_rules()


@router.post("/rules", response_model=TriggerRule)
def create_rule(rule: TriggerRule, storage: Storage = Depends(get_db_storage)):
    """Create a new trigger rule."""
    storage.save_rule(rule)
    return rule


@router.put("/rules/{rule_id}", response_model=TriggerRule)
def update_rule(rule_id: str, rule: TriggerRule, storage: Storage = Depends(get_db_storage)):
    """Update an existing trigger rule."""
    rule.id = rule_id
    storage.save_rule(rule)
    return rule


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: str, storage: Storage = Depends(get_db_storage)):
    """Delete a trigger rule."""
    success = storage.delete_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found.")
    return {"status": "success", "message": f"Rule {rule_id} deleted."}


# ==========================================
# FAQs
# ==========================================

@router.get("/faqs", response_model=List[FAQItem])
def list_faqs(storage: Storage = Depends(get_db_storage)):
    """List all FAQ entries."""
    return storage.get_faqs()


@router.post("/faqs", response_model=FAQItem)
def create_faq(faq: FAQItem, storage: Storage = Depends(get_db_storage)):
    """Create a new FAQ and invalidate/re-fit TF-IDF vectorizer."""
    storage.save_faq(faq)
    invalidate_faq_cache(storage)
    return faq


@router.put("/faqs/{faq_id}", response_model=FAQItem)
def update_faq(faq_id: str, faq: FAQItem, storage: Storage = Depends(get_db_storage)):
    """Update an FAQ and invalidate/re-fit TF-IDF vectorizer."""
    faq.id = faq_id
    storage.save_faq(faq)
    invalidate_faq_cache(storage)
    return faq


@router.delete("/faqs/{faq_id}")
def delete_faq(faq_id: str, storage: Storage = Depends(get_db_storage)):
    """Delete an FAQ and invalidate/re-fit TF-IDF vectorizer."""
    success = storage.delete_faq(faq_id)
    if not success:
        raise HTTPException(status_code=404, detail="FAQ not found.")
    invalidate_faq_cache(storage)
    return {"status": "success", "message": f"FAQ {faq_id} deleted."}


# ==========================================
# FLOWS
# ==========================================

@router.get("/flows", response_model=List[QualificationFlow])
def list_flows(storage: Storage = Depends(get_db_storage)):
    """List all lead qualification flows."""
    return storage.get_flows()


@router.get("/flows/{flow_id}", response_model=QualificationFlow)
def get_flow(flow_id: str, storage: Storage = Depends(get_db_storage)):
    """Get flow definition by ID."""
    flow = storage.get_flow(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found.")
    return flow


@router.put("/flows/{flow_id}", response_model=QualificationFlow)
def update_flow(
    flow_id: str, flow: QualificationFlow, storage: Storage = Depends(get_db_storage)
):
    """Save or update qualification flow (JSON structure)."""
    flow.id = flow_id
    storage.save_flow(flow)
    return flow


# ==========================================
# LEADS & CSV EXPORT
# ==========================================

@router.get("/leads", response_model=List[Lead])
def list_leads(
    tier: Optional[str] = Query(None, description="Filter by HOT, WARM, or COLD"),
    storage: Storage = Depends(get_db_storage),
):
    """List captured leads, optionally filtered by tier."""
    leads = storage.get_leads()
    if tier:
        tier_upper = tier.upper().strip()
        leads = [l for l in leads if l.tier.value == tier_upper]
    return leads


@router.get("/leads/export")
def export_leads_csv(storage: Storage = Depends(get_db_storage)):
    """Export captured leads as a CSV file."""
    leads = storage.get_leads()
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["ID", "Channel", "User ID", "Username", "Email", "Score", "Tier", "Flow ID", "Captured At"])

    for lead in leads:
        writer.writerow(
            [
                lead.id,
                lead.channel,
                lead.user_id,
                lead.username or "",
                lead.email or "",
                lead.score,
                lead.tier.value,
                lead.flow_id,
                lead.created_at.isoformat() if lead.created_at else "",
            ]
        )

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=funnelbot_leads.csv"},
    )


# ==========================================
# CONVERSATION LOGS
# ==========================================

@router.get("/conversations")
def list_conversation_logs(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    storage: Storage = Depends(get_db_storage),
):
    """Paginated conversation logs for admin review."""
    return storage.get_conversation_logs(limit=limit, offset=offset)


# ==========================================
# ANALYTICS
# ==========================================

@router.get("/analytics")
def get_analytics(
    session: Session = Depends(get_session),
    storage: Storage = Depends(get_db_storage),
):
    """
    Funnel analytics: comments triggered, DMs sent, lead tiers,
    completion rate, and drop-off per step.
    """
    leads = storage.get_leads()
    total_leads = len(leads)
    leads_by_tier = {"HOT": 0, "WARM": 0, "COLD": 0}
    for l in leads:
        t = l.tier.value
        if t in leads_by_tier:
            leads_by_tier[t] += 1

    # Query log counts from DB
    total_comments = session.exec(
        select(func.count(ConversationLogDB.id)).where(ConversationLogDB.event_type == "comment")
    ).one() or 0

    total_dms = session.exec(
        select(func.count(ConversationLogDB.id)).where(ConversationLogDB.event_type == "dm")
    ).one() or 0

    # Query state completion
    states = session.exec(select(ConversationStateDB)).all()
    total_conversations = len(states)
    completed_conversations = sum(1 for s in states if s.status == "completed")
    active_conversations = sum(1 for s in states if s.status == "active")

    completion_rate = (
        round((completed_conversations / total_conversations) * 100, 1)
        if total_conversations > 0
        else 0.0
    )

    # Step drop-off breakdown
    drop_off_per_step: Dict[str, int] = {}
    for s in states:
        step_id = s.current_step_id or ("completed" if s.status == "completed" else "unknown")
        drop_off_per_step[step_id] = drop_off_per_step.get(step_id, 0) + 1

    return {
        "total_comments_triggered": total_comments,
        "total_dms_received": total_dms,
        "total_leads": total_leads,
        "leads_by_tier": leads_by_tier,
        "completion_rate_percent": completion_rate,
        "active_conversations": active_conversations,
        "funnel_drop_off": drop_off_per_step,
    }
