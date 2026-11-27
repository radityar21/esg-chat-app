"""Report Builder: catalog, versioned section templates and saved report configurations.

Templates
    live (what the generator reads)   s3://<kb bucket>/prompts/templates/<file>
    versions                          s3://<kb bucket>/template-versions/<file>/<version>.json
    index                             s3://<kb bucket>/template-versions/<file>/index.json
A version is a draft until an administrator publishes it; publishing copies its text to the live key. The first time a
template is opened, the live text is recorded as version v1 (author "repository") so it can always be restored.
Drafts may also come from the AgentCore agent (author "agent", e.g. after a regulatory finding was analysed).

Saved configurations
    s3://<output bucket>/report-configs/<id>.json   name, framework, sections, language
"""

from __future__ import annotations

import json
import re
import time
import uuid
from typing import Any, Callable

from . import common

try:
    import report_catalog as catalog
except ImportError:  # pragma: no cover
    from _shared import report_catalog as catalog  # type: ignore

PLACEHOLDER = re.compile(r"\{[a-z_]+\}")
MIN_LEN, MAX_LEN = 200, 30000
CONFIG_ID = re.compile(r"^[a-z0-9]{12}$")


def _kb_bucket() -> str:
    return f"esg-kb-documents-{common.ACCOUNT_ID}"


class Store:
    """S3 text/JSON access. Replaced by a fake in tests."""

    def get_text(self, bucket: str, key: str) -> str | None:
        s3 = common.client("s3")
        try:
            return s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
        except s3.exceptions.NoSuchKey:
            return None

    def put_text(self, bucket: str, key: str, text: str) -> None:
        common.client("s3").put_object(Bucket=bucket, Key=key, Body=text.encode("utf-8"), ContentType="text/plain; charset=utf-8")

    def get_json(self, bucket: str, key: str) -> Any:
        t = self.get_text(bucket, key)
        return json.loads(t) if t else None

    def put_json(self, bucket: str, key: str, body: Any) -> None:
        common.client("s3").put_object(Bucket=bucket, Key=key, Body=common.dumps(body).encode(), ContentType="application/json")

    def list_keys(self, bucket: str, prefix: str) -> list[str]:
        out: list[str] = []
        for page in common.client("s3").get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
            out += [o["Key"] for o in page.get("Contents", [])]
        return out

    def delete(self, bucket: str, key: str) -> None:
        common.client("s3").delete_object(Bucket=bucket, Key=key)


STORE = Store()
now = lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())  # noqa: E731


# ── catalog ───────────────────────────────────────────────────────────────────────────────────────
def get_catalog(_params: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"frameworks": [{"id": k, "label": v["label"], "sections": [{"id": s, **{x: catalog.SECTIONS[s][x] for x in ("label", "desc")}} for s in v["sections"]]}
                           for k, v in catalog.FRAMEWORKS.items()],
            "languages": [{"id": k, "label": v} for k, v in catalog.LANGUAGES.items()], "default_language": catalog.DEFAULT_LANGUAGE,
            "years": [2023, 2024], "note": "Sections follow the framework's fixed document order; you choose which ones to include."}


# ── templates ─────────────────────────────────────────────────────────────────────────────────────
def _file(key: str) -> str:
    if key not in catalog.SECTIONS:
        raise ValueError(f"Unknown template {key!r}")
    return catalog.template_file(key)


def _index(file: str, store: Store) -> dict[str, Any]:
    bucket = _kb_bucket()
    idx = store.get_json(bucket, f"template-versions/{file}/index.json")
    if idx:
        return idx
    live = store.get_text(bucket, f"prompts/templates/{file}")
    if live is None:
        raise LookupError(f"Template {file} is not uploaded yet (run scripts/upload_kb_documents.py)")
    idx = {"published": "v1", "versions": [{"version": "v1", "status": "published", "author": "repository", "created_at": now(),
                                            "published_at": now(), "note": "Initial version from the repository"}]}
    store.put_json(bucket, f"template-versions/{file}/v1.json", {"version": "v1", "text": live})
    store.put_json(bucket, f"template-versions/{file}/index.json", idx)
    return idx


def get_template(key: str, store: Store | None = None) -> dict[str, Any]:
    store = store or STORE
    file = _file(key)
    idx = _index(file, store)
    bucket = _kb_bucket()
    texts = {v["version"]: (store.get_json(bucket, f"template-versions/{file}/{v['version']}.json") or {}).get("text", "") for v in idx["versions"]}
    meta = catalog.SECTIONS[key]
    return {"key": key, "file": file, "label": meta["label"], "desc": meta["desc"], "published": idx["published"],
            "placeholders": sorted(set(PLACEHOLDER.findall(texts.get(idx["published"], "")))),
            "versions": [{**v, "text": texts.get(v["version"], "")} for v in reversed(idx["versions"])]}


def validate_text(text: str, published_text: str) -> list[str]:
    """Problems that would break the generator. An empty list means the draft can be saved."""
    problems = []
    if not MIN_LEN <= len(text) <= MAX_LEN:
        problems.append(f"The template must be between {MIN_LEN} and {MAX_LEN} characters (now {len(text)}).")
    missing = sorted(set(PLACEHOLDER.findall(published_text)) - set(PLACEHOLDER.findall(text)))
    if missing:
        problems.append("These data placeholders are required and were removed: " + ", ".join(missing))
    unknown = sorted(set(PLACEHOLDER.findall(text)) - set(PLACEHOLDER.findall(published_text)))
    if unknown:
        problems.append("New placeholders are not filled by the generator: " + ", ".join(unknown) + ". Use only the existing ones.")
    if "```" in text:
        problems.append("Code fences (```) are not allowed in a template.")
    return problems


def save_draft(key: str, text: str, note: str, author: str, store: Store | None = None) -> dict[str, Any]:
    store = store or STORE
    file = _file(key)
    text = str(text or "").replace("\r\n", "\n")
    idx = _index(file, store)
    bucket = _kb_bucket()
    published_text = (store.get_json(bucket, f"template-versions/{file}/{idx['published']}.json") or {}).get("text", "")
    problems = validate_text(text, published_text)
    if problems:
        return {"saved": False, "problems": problems}
    n = max(int(v["version"][1:]) for v in idx["versions"]) + 1
    version = f"v{n}"
    store.put_json(bucket, f"template-versions/{file}/{version}.json", {"version": version, "text": text})
    idx["versions"].append({"version": version, "status": "draft", "author": author[:80], "created_at": now(), "note": str(note or "")[:500]})
    store.put_json(bucket, f"template-versions/{file}/index.json", idx)
    return {"saved": True, "version": version}


def publish(key: str, version: str, by: str, store: Store | None = None) -> dict[str, Any]:
    store = store or STORE
    file = _file(key)
    idx = _index(file, store)
    bucket = _kb_bucket()
    entry = next((v for v in idx["versions"] if v["version"] == version), None)
    if not entry:
        raise ValueError(f"Unknown version {version!r}")
    body = store.get_json(bucket, f"template-versions/{file}/{version}.json") or {}
    store.put_text(bucket, f"prompts/templates/{file}", body.get("text", ""))
    for v in idx["versions"]:
        if v["status"] == "published":
            v["status"] = "archived"
    entry.update({"status": "published", "published_at": now(), "published_by": by[:80]})
    idx["published"] = version
    store.put_json(bucket, f"template-versions/{file}/index.json", idx)
    return {"published": version, "note": "Reports generated from now on use this version."}


# ── saved configurations ──────────────────────────────────────────────────────────────────────────
def _check_config(body: dict[str, Any]) -> dict[str, Any]:
    fw = str(body.get("framework", ""))
    language = str(body.get("language") or catalog.DEFAULT_LANGUAGE)
    sections = [str(s) for s in (body.get("sections") or [])] or None
    tmpl = catalog.section_templates(fw, sections, language)  # raises ValueError on a bad request
    name = str(body.get("name") or "").strip()[:80]
    if not name:
        raise ValueError("Give the configuration a name")
    return {"name": name, "framework": fw, "language": language, "sections": [t["template_id"] for t in tmpl]}


def list_configs(_params: dict[str, Any] | None = None, store: Store | None = None) -> dict[str, Any]:
    store = store or STORE
    out = []
    for k in store.list_keys(common.OUTPUT_BUCKET, "report-configs/"):
        c = store.get_json(common.OUTPUT_BUCKET, k)
        if c:
            out.append(c)
    return {"configs": sorted(out, key=lambda c: c.get("updated_at", ""), reverse=True)}


def get_config(config_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or STORE
    if not CONFIG_ID.match(config_id or ""):
        raise ValueError("invalid configuration id")
    c = store.get_json(common.OUTPUT_BUCKET, f"report-configs/{config_id}.json")
    if not c:
        raise LookupError("configuration not found")
    return c


def save_config(body: dict[str, Any], by: str, store: Store | None = None) -> dict[str, Any]:
    store = store or STORE
    c = _check_config(body)
    cid = str(body.get("id") or "") or uuid.uuid4().hex[:12]
    if not CONFIG_ID.match(cid):
        raise ValueError("invalid configuration id")
    c.update({"id": cid, "updated_at": now(), "updated_by": by[:80]})
    store.put_json(common.OUTPUT_BUCKET, f"report-configs/{cid}.json", c)
    return c


def delete_config(config_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or STORE
    get_config(config_id, store)
    store.delete(common.OUTPUT_BUCKET, f"report-configs/{config_id}.json")
    return {"deleted": config_id}


# ── generate (through the AgentCore orchestrator) ────────────────────────────────────────────────
def generate_request(body: dict[str, Any]) -> dict[str, Any]:
    """Validate a generate request and return the runtime payload. The platform queues it like a chat turn."""
    if body.get("config_id"):
        c = get_config(str(body["config_id"]))
        framework, sections, language = c["framework"], c["sections"], c["language"]
    else:
        framework, language = str(body.get("framework", "")), str(body.get("language") or catalog.DEFAULT_LANGUAGE)
        sections = [str(s) for s in (body.get("sections") or [])] or None
    catalog.section_templates(framework, sections, language)
    try:
        year = int(body.get("reporting_year"))
    except (TypeError, ValueError):
        raise ValueError("reporting_year is required") from None
    if year not in (2023, 2024):
        raise ValueError("Data is only available for 2023 and 2024")
    return {"mode": "start", "pipeline": "esg_report", "reporting_year": year, "framework": framework, "language": language, "sections": sections}


def handlers(user: Callable[[dict[str, Any]], str]) -> dict[str, Callable[[dict[str, Any]], Any]]:
    """Direct-invocation actions (the agent uses template_propose and report_config_get)."""
    return {
        "report_catalog": get_catalog,
        "report_configs": list_configs,
        "report_config_get": lambda p: get_config(str(p.get("config_id", ""))),
        "template_get": lambda p: get_template(str(p.get("template_key", ""))),
        "template_propose": lambda p: save_draft(str(p.get("template_key", "")), str(p.get("text", "")),
                                                 f"AI proposal: {str(p.get('reason', ''))[:400]}", "agent"),
    }
