"""Compliance Intelligence: PSPK readiness (gap analyzer) and regulatory change detection."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable

from . import common

CONFIG = json.loads((Path(__file__).parent / "config" / "pspk_checklist.json").read_text())
ATTEST_KEY = "compliance/attestations.json"
ALERTS_KEY = "compliance/alerts.json"
SEEN_KEY = "compliance/seen.json"
SCENARIO_RUN_KEY = "platform/scenario_last_run.json"
VALID_STATUS = {"ready", "partial", "gap"}
COVERAGE = {"ready": 1.0, "partial": 0.5, "gap": 0.0}

Q = common.athena


def _probe(item: dict[str, Any], year: int, att: dict[str, Any], summary: dict[str, Any], q: Callable[..., Any]) -> tuple[str, str]:
    """Return (status, evidence) for one checklist item."""
    p = item["probe"]
    t = p["type"]
    try:
        if t == "athena_rows":
            n = (q(p["sql"].format(year=year), p["db"]) or [{}])[0].get("n") or 0
            return ("ready", f"{n:,} rows for {year}") if n > 0 else ("gap", f"no rows for {year}")
        if t == "pcaf_quality":
            s = summary.get("avg_pcaf_data_quality")
            if s is None:
                return "gap", "no PCAF score available"
            return (("ready" if s <= p["ready_max"] else "partial" if s <= p["partial_max"] else "gap"), f"weighted PCAF score {s:.2f}")
        if t == "assurance":
            lvl = summary.get("assurance_level") or "none"
            return (("ready" if lvl in ("limited", "reasonable") else "gap"), f"assurance level: {lvl}")
        if t == "scenario_run":
            last = common.s3_get(SCENARIO_RUN_KEY)
            if last and time.time() - last.get("ts", 0) < 90 * 86400:
                return "ready", "scenario analysis run in the last 90 days"
            return "partial", "scenario engine available, no recent run stored"
    except Exception as exc:  # noqa: BLE001 - a failing probe must degrade the item, not the endpoint
        return "gap", f"probe error: {str(exc)[:120]}"
    # attestation
    a = (att or {}).get(item["id"])
    if a and a.get("status") in VALID_STATUS:
        return a["status"], f"attested by {a.get('by', 'user')} on {a.get('at', '?')}: {a.get('note', '')}".strip()
    return p.get("default_status", "gap"), "no evidence on file (default)"


def score(items: list[dict[str, Any]]) -> float:
    tot = sum(i["w"] for i in items)
    return round(sum(i["w"] * COVERAGE[i["status"]] for i in items) / tot * 100, 1) if tot else 0.0


def readiness(year: int, q: Callable[..., Any] | None = None) -> dict[str, Any]:
    q = q or Q
    att = common.s3_get(ATTEST_KEY) or {}
    try:
        summary = (q(f"SELECT avg_pcaf_data_quality, assurance_level FROM esg_aggregated.ghg_summary_annual WHERE reporting_year = {year} LIMIT 1", "esg_aggregated") or [{}])[0]
    except Exception:  # noqa: BLE001
        summary = {}
    items = []
    for it in CONFIG["items"]:
        status, evidence = _probe(it, year, att, summary, q)
        items.append({k: it[k] for k in ("id", "pillar", "req", "w", "system")} | {"status": status, "evidence": evidence,
                                                                                  "rec": it.get("rec", "") if status != "ready" else ""})
    pillars = [{**p, "score": score([i for i in items if i["pillar"] == p["id"]])} for p in CONFIG["pillars"]]
    return {"source": "athena", "year": year, "score": score(items), "pillars": pillars, "items": items,
            "counts": {s: sum(1 for i in items if i["status"] == s) for s in ("ready", "partial", "gap")}, "checklist_version": CONFIG["version"]}


def attest(body: dict[str, Any]) -> dict[str, Any]:
    iid, status = body.get("item_id"), body.get("status")
    if iid not in {i["id"] for i in CONFIG["items"]} or status not in VALID_STATUS:
        raise ValueError("item_id must be a checklist id and status one of ready|partial|gap")
    att = common.s3_get(ATTEST_KEY) or {}
    att[iid] = {"status": status, "note": str(body.get("note", ""))[:300], "by": str(body.get("by", "user"))[:60], "at": time.strftime("%Y-%m-%d")}
    common.s3_put(ATTEST_KEY, att)
    return {"ok": True, "item_id": iid, "status": status}


# ── regulatory change detection ───────────────────────────────────────────────────────────────────
_A_RE = re.compile(r'<a\b[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', re.I | re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def _fetch(url: str, timeout: int = 10) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "esg-reg-monitor/1.0 (+compliance)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - fixed allow-list of public URLs from config
        return r.read(1_500_000).decode("utf-8", "ignore")


def extract_items(html: str, base_url: str, keywords: list[str]) -> list[dict[str, str]]:
    out, seen = [], set()
    for href, inner in _A_RE.findall(html):
        title = re.sub(r"\s+", " ", _TAG_RE.sub("", inner)).strip()
        if len(title) < 15 or title.lower() in seen:
            continue
        if any(k in title.lower() for k in keywords):
            seen.add(title.lower())
            url = href if href.startswith("http") else base_url.rstrip("/") + "/" + href.lstrip("/")
            out.append({"title": title[:240], "url": url})
    return out[:40]


def _classify(title: str, source: str) -> dict[str, Any]:
    """Impact classification with Haiku (task reg_classifier). Falls back to a neutral record if Bedrock is unavailable."""
    fallback = {"severity": "low", "impact": ["Review manually"], "action": "Review the publication and decide whether a template change is needed.", "classified": False}
    try:
        from model_routing import resolve
        from usage_meter import record

        alias, mid = resolve("reg_classifier")
        prompt = ("You monitor Indonesian and international sustainability regulation for a bank. Given a publication title, reply with ONLY JSON: "
                  '{"severity":"high|medium|low","impact":["report section names affected, e.g. Governance, Metrics & Targets, Scope 3"],'
                  '"action":"one sentence on what to change in the report template"}. '
                  f"Source: {source}\nTitle: {title}")
        r = common.client("bedrock-runtime").converse(modelId=mid, messages=[{"role": "user", "content": [{"text": prompt}]}],
                                                      inferenceConfig={"maxTokens": 300, "temperature": 0})
        text = r["output"]["message"]["content"][0]["text"]
        data = json.loads(text[text.index("{"): text.rindex("}") + 1])
        record("reg_classifier", mid, r["usage"]["inputTokens"], r["usage"]["outputTokens"], source="reg_monitor")
        sev = data.get("severity", "low")
        return {"severity": sev if sev in ("high", "medium", "low") else "low", "impact": list(data.get("impact", []))[:5] or ["Review manually"],
                "action": str(data.get("action", fallback["action"]))[:300], "classified": True}
    except Exception:  # noqa: BLE001
        return fallback


def scan(fetch: Callable[[str], str] | None = None, classify: Callable[[str, str], dict[str, Any]] | None = None) -> dict[str, Any]:
    fetch, classify = fetch or _fetch, classify or _classify
    seen = set(common.s3_get(SEEN_KEY) or [])
    alerts = common.s3_get(ALERTS_KEY) or {"alerts": []}
    new, errors = [], []
    for src in CONFIG["sources"]:
        try:
            html = fetch(src["url"])
        except Exception as exc:  # noqa: BLE001
            errors.append({"source": src["name"], "error": str(exc)[:120]})
            continue
        for it in extract_items(html, src["url"], CONFIG["keywords"]):
            h = hashlib.sha256(f"{src['id']}|{it['title']}".encode()).hexdigest()[:16]
            if h in seen:
                continue
            seen.add(h)
            c = classify(it["title"], src["name"])
            new.append({"id": f"A-{h[:6].upper()}", "date": time.strftime("%Y-%m-%d"), "source": src["name"], "title": it["title"], "url": it["url"],
                        "severity": c["severity"], "impact": c["impact"], "action": c["action"], "classified": c["classified"], "isNew": True})
    if new or not alerts.get("alerts"):
        for a in alerts["alerts"]:
            a["isNew"] = False
        alerts["alerts"] = (new + alerts["alerts"])[:100]
    alerts["last_scan"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    alerts["last_errors"] = errors
    common.s3_put(ALERTS_KEY, alerts)
    common.s3_put(SEEN_KEY, sorted(seen))
    return {"new": len(new), "alerts": alerts["alerts"][:20], "errors": errors, "sources": [s["name"] for s in CONFIG["sources"]], "last_scan": alerts["last_scan"]}


def alerts() -> dict[str, Any]:
    d = common.s3_get(ALERTS_KEY) or {"alerts": [], "last_scan": None}
    return {"alerts": d.get("alerts", [])[:50], "last_scan": d.get("last_scan"), "sources": [s["name"] for s in CONFIG["sources"]], "errors": d.get("last_errors", [])}
