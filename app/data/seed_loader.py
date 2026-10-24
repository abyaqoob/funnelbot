"""Loader for seed rules, FAQs, and qualification flows."""
import json
from pathlib import Path
from typing import Any, Dict
from app.engine.storage import Storage
from app.models.faq import FAQItem
from app.models.flow import QualificationFlow
from app.models.rules import TriggerRule

SEED_FILE = Path(__file__).parent / "seed.json"


def load_seed_data(storage: Storage, filepath: Path = SEED_FILE) -> Dict[str, int]:
    """Loads default seed rules, FAQs, and flows into storage."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    rules_count = 0
    for r_data in data.get("rules", []):
        rule = TriggerRule(**r_data)
        storage.save_rule(rule)
        rules_count += 1

    faqs_count = 0
    for f_data in data.get("faqs", []):
        faq = FAQItem(**f_data)
        storage.save_faq(faq)
        faqs_count += 1

    flows_count = 0
    for fl_data in data.get("flows", []):
        flow = QualificationFlow(**fl_data)
        storage.save_flow(flow)
        flows_count += 1

    return {"rules": rules_count, "faqs": faqs_count, "flows": flows_count}
