import json
import re
from datetime import date, time
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .ingest import candidates, normalize
from .models import FIELDS, FORMATS

UNKNOWN = {"unknown", "tbd", "tbc", "n/a", "pending", "not confirmed", "none"}


def valid_field(key, value):
    if not value.strip() or normalize(value) in UNKNOWN:
        return False
    try:
        if key == "date":
            return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)) and bool(date.fromisoformat(value))
        if key in {"start_time", "end_time"}:
            return bool(re.fullmatch(r"\d{2}:\d{2}", value)) and bool(time.fromisoformat(value))
        if key == "timezone":
            ZoneInfo(value)
        if key == "registration_url":
            parsed = urlparse(value)
            return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not re.search(r"\s", value)
        if key == "price":
            return bool(re.search(r"\b(free|no charge|INR|USD|EUR|GBP|Rs)\b|[₹$€£]", value, re.I))
        return len(value) <= 1000
    except (ValueError, KeyError):
        return False


def resolve(docs, plan, confirmations):
    seen = candidates(docs)
    sources = {d["id"]: d["text"] for d in docs}
    for key, fact in plan.get("facts", {}).items():
        if key not in FIELDS:
            continue
        ids = fact.get("source_ids", [])
        quote, value = fact.get("quote", ""), fact.get("value", "")
        supported = bool(ids) and all(i in sources for i in ids) and any(
            normalize(quote) in normalize(sources[i]) and normalize(value) in normalize(quote) for i in ids)
        if supported and normalize(value) not in UNKNOWN:
            seen[key].append(fact)
    facts, questions = {}, []
    for key in FIELDS:
        values = {}
        for fact in seen[key]:
            comparison = fact["value"].strip() if key == "registration_url" else normalize(fact["value"])
            values.setdefault(comparison, fact)
        if key in confirmations:
            facts[key] = confirmations[key]
        elif len(values) == 1:
            facts[key] = next(iter(values.values()))
        if len(values) > 1 and key not in confirmations:
            questions.append({"key": key, "reason": "Conflicting sources; explicitly confirm the authoritative value.", "candidates": list(values.values())})
        elif key not in facts or not valid_field(key, facts[key]["value"]):
            facts.pop(key, None)
            hint = {"date": "Use YYYY-MM-DD.", "start_time": "Use HH:MM, 24-hour time.",
                    "end_time": "Use HH:MM, 24-hour time.", "timezone": "Use an IANA timezone, e.g. Asia/Kolkata.",
                    "price": "Include a currency (e.g. INR 100) or Free.",
                    "registration_url": "Provide the confirmed HTTPS registration URL."}.get(key, "")
            questions.append({"key": key, "reason": f"Missing, unsupported or invalid essential fact. {hint}", "candidates": list(values.values())})
    if all(k in facts for k in ("start_time", "end_time")):
        if facts["end_time"]["value"] <= facts["start_time"]["value"]:
            facts.pop("end_time", None)
            questions.append({"key": "end_time", "reason": "End time must follow start time on the same date for this MVP.", "candidates": []})
    for i, question in enumerate(plan.get("questions", [])):
        key = f"planner_{i}"
        if key not in confirmations:
            questions.append({"key": key, "reason": question, "candidates": []})
    return facts, questions


def fact_card(facts):
    f = {key: fact["value"] for key, fact in facts.items()}
    return (f"Event: {f['event_name']}\nDate: {f['date']}\n"
            f"Time: {f['start_time']}–{f['end_time']} ({f['timezone']})\n"
            f"Venue: {f['venue']}\nPrice: {f['price']}\nRegister: {f['registration_url']}")


def render(bundle, facts, demo=False):
    card = fact_card(facts)
    prefix = "FICTIONAL DEMO — not a real event. No audience results are claimed.\n\n" if demo else ""
    drafts = {}
    for key in FORMATS:
        if key == "ads":
            drafts[key] = "\n\n---\n\n".join(f"{prefix}Ad variation {i}\n\n{item['text']}\n\n{card}"
                                                       for i, item in enumerate(bundle[key], 1))
        else:
            drafts[key] = f"{prefix}{bundle[key]['text']}\n\n{card}"
    return drafts


def deterministic_review(drafts, facts, docs, bundle=None, demo=False):
    issues = []
    card = fact_card(facts)
    for key in FORMATS:
        text = drafts.get(key, "")
        expected = 3 if key == "ads" else 1
        if text.count(card) != expected:
            issues.append({"format": key, "severity": "blocking", "detail": "Critical fact block is missing or changed. Restore the confirmed date, time, venue, price and link exactly."})
        if demo and text.count("FICTIONAL DEMO — not a real event.") < expected:
            issues.append({"format": key, "severity": "blocking", "detail": "Fictional demo label was removed."})
        body = text.replace(card, "")
        body = re.sub(r"Ad variation [123]", "Ad variation", body)
        # Keep all critical values in the deterministic card. Alternate numeric/link renderings need human repair.
        if re.search(r"\d|https?://|\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|January|February|March|April|June|July|August|September|October|November|December)\b", body, re.I) or re.search(r"\bMay\b", body):
            issues.append({"format": key, "severity": "blocking", "detail": "Narrative contains numbers, a date/day/month or a URL outside the confirmed fact block. Remove alternate critical details; use the fact block."})
        if re.search(r"(?:venue|price|date|time|register)\s*:", body, re.I):
            issues.append({"format": key, "severity": "blocking", "detail": "Narrative repeats a labelled critical field outside the confirmed fact block."})
    if bundle:
        valid_ids = {d["id"] for d in docs} | {i for f in facts.values() for i in f["source_ids"]}
        for key in FORMATS:
            for draft in bundle[key] if key == "ads" else [bundle[key]]:
                if any(i not in valid_ids for i in draft["source_ids"]):
                    issues.append({"format": key, "severity": "blocking", "detail": "Draft cites an unknown source."})
    return issues


def model_context(state, docs):
    return json.dumps({"confirmed_facts": state["facts"], "evidence": docs,
                       "clarifications": state.get("clarification_history", []),
                       "approach": state["plan"]["approach"]}, ensure_ascii=False)
