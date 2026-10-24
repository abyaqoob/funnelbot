"""Integration tests for Admin API endpoints (Rules, FAQs, Flows, Leads, Analytics)."""
from fastapi.testclient import TestClient
from app.config import settings

AUTH_HEADERS = {"X-Admin-Password": settings.ADMIN_PASSWORD}


def test_admin_demo_mode_security(client: TestClient):
    # GET allowed in demo mode without auth
    res_get = client.get("/api/admin/rules")
    assert res_get.status_code == 200

    # POST rejected without auth
    res_post_unauth = client.post(
        "/api/admin/rules",
        json={
            "id": "unauth_rule",
            "name": "Unauth",
            "keywords": ["test"],
            "match_mode": "exact",
        },
    )
    assert res_post_unauth.status_code == 401

    # POST succeeds with auth header
    res_post_auth = client.post(
        "/api/admin/rules",
        json={
            "id": "auth_rule",
            "name": "Auth Rule",
            "keywords": ["test"],
            "match_mode": "exact",
        },
        headers=AUTH_HEADERS,
    )
    assert res_post_auth.status_code == 200


def test_admin_rules_crud(client: TestClient):
    # 1. Create Rule
    new_rule = {
        "id": "rule_bonus",
        "name": "Bonus Rule",
        "keywords": ["bonus", "gift"],
        "match_mode": "fuzzy",
        "fuzzy_threshold": 80.0,
        "reply_templates": ["Enjoy your gift @{username}!"],
        "flow_id": "lead_qualification",
        "is_active": True,
    }
    res_create = client.post("/api/admin/rules", json=new_rule, headers=AUTH_HEADERS)
    assert res_create.status_code == 200
    assert res_create.json()["id"] == "rule_bonus"

    # 2. List Rules
    res_list = client.get("/api/admin/rules")
    assert any(r["id"] == "rule_bonus" for r in res_list.json())

    # 3. Update Rule
    new_rule["name"] = "Updated Bonus Rule"
    res_update = client.put("/api/admin/rules/rule_bonus", json=new_rule, headers=AUTH_HEADERS)
    assert res_update.status_code == 200
    assert res_update.json()["name"] == "Updated Bonus Rule"

    # 4. Delete Rule
    res_delete = client.delete("/api/admin/rules/rule_bonus", headers=AUTH_HEADERS)
    assert res_delete.status_code == 200

    # 5. Delete non-existent rule -> 404
    res_del_404 = client.delete("/api/admin/rules/non_existent", headers=AUTH_HEADERS)
    assert res_del_404.status_code == 404


def test_admin_faqs_crud(client: TestClient):
    # 1. Create FAQ
    new_faq = {
        "id": "faq_custom_warranty",
        "category": "Policy",
        "question": "What is your hardware warranty?",
        "question_variants": ["Warranty coverage", "Hardware replacement"],
        "answer": "We offer a 2-year full replacement warranty.",
        "is_active": True,
    }
    res_create = client.post("/api/admin/faqs", json=new_faq, headers=AUTH_HEADERS)
    assert res_create.status_code == 200

    # 2. Update FAQ
    new_faq["answer"] = "Updated 3-year warranty."
    res_update = client.put("/api/admin/faqs/faq_custom_warranty", json=new_faq, headers=AUTH_HEADERS)
    assert res_update.status_code == 200
    assert res_update.json()["answer"] == "Updated 3-year warranty."

    # 3. Delete FAQ
    res_delete = client.delete("/api/admin/faqs/faq_custom_warranty", headers=AUTH_HEADERS)
    assert res_delete.status_code == 200


def test_admin_flows(client: TestClient):
    # 1. List flows
    res_list = client.get("/api/admin/flows")
    assert res_list.status_code == 200
    assert len(res_list.json()) > 0

    # 2. Get flow by ID
    res_get = client.get("/api/admin/flows/lead_qualification")
    assert res_get.status_code == 200
    flow = res_get.json()
    assert flow["id"] == "lead_qualification"

    # 3. Update flow
    flow["title"] = "Updated Qualification Flow"
    res_put = client.put("/api/admin/flows/lead_qualification", json=flow, headers=AUTH_HEADERS)
    assert res_put.status_code == 200
    assert res_put.json()["title"] == "Updated Qualification Flow"


def test_admin_leads_and_csv_export(client: TestClient):
    # Generate a lead by simulating flow completion
    user_id = "recruiter_csv_test"
    client.post(
        "/api/simulator/event",
        json={"channel": "simulator", "event_type": "comment", "user_id": user_id, "username": "csv_lead", "text": "GUIDE"},
    )
    client.post(
        "/api/simulator/event",
        json={"channel": "simulator", "event_type": "dm", "user_id": user_id, "username": "csv_lead", "text": "1"},
    )
    client.post(
        "/api/simulator/event",
        json={"channel": "simulator", "event_type": "dm", "user_id": user_id, "username": "csv_lead", "text": "1"},
    )
    client.post(
        "/api/simulator/event",
        json={"channel": "simulator", "event_type": "dm", "user_id": user_id, "username": "csv_lead", "text": "1"},
    )
    client.post(
        "/api/simulator/event",
        json={"channel": "simulator", "event_type": "dm", "user_id": user_id, "username": "csv_lead", "text": "lead@company.com"},
    )

    # 1. List Leads
    res_leads = client.get("/api/admin/leads")
    assert res_leads.status_code == 200
    leads = res_leads.json()
    assert len(leads) >= 1
    assert any(l["email"] == "lead@company.com" for l in leads)

    # 2. Filter Leads by tier
    res_hot = client.get("/api/admin/leads?tier=HOT")
    assert res_hot.status_code == 200
    assert all(l["tier"] == "HOT" for l in res_hot.json())

    # 3. Export CSV
    res_csv = client.get("/api/admin/leads/export")
    assert res_csv.status_code == 200
    assert res_csv.headers["content-type"].startswith("text/csv")
    csv_text = res_csv.text
    assert "ID,Channel,User ID,Username,Email,Score,Tier,Flow ID,Captured At" in csv_text
    assert "lead@company.com" in csv_text


def test_admin_conversations_and_analytics(client: TestClient):
    # Query conversation logs
    res_logs = client.get("/api/admin/conversations?limit=10")
    assert res_logs.status_code == 200
    assert isinstance(res_logs.json(), list)

    # Query analytics
    res_analytics = client.get("/api/admin/analytics")
    assert res_analytics.status_code == 200
    analytics = res_analytics.json()
    assert "total_comments_triggered" in analytics
    assert "total_dms_received" in analytics
    assert "total_leads" in analytics
    assert "leads_by_tier" in analytics
    assert "completion_rate_percent" in analytics
    assert "funnel_drop_off" in analytics
