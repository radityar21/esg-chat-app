"""PII detection and masking for HR / employee data before it reaches an LLM (UU PDP No. 27/2022).

Design:
  * Deterministic, dependency-free detectors (NIK, NPWP, phone, email, honorific names, roster names).
  * Column-aware policy for structured records (identifiers tokenized, salary and birth date generalized).
  * Pseudonymization uses HMAC-SHA256 with ``PII_TOKEN_SECRET`` so tokens are stable across runs but not
    reversible without the secret. A reversible vault is intentionally out of scope.
  * Optional Amazon Bedrock Guardrails pass via ``PII_GUARDRAIL_ID`` / ``PII_GUARDRAIL_VERSION`` as a second layer.

Findings never contain the raw values, only type and position counts, so they are safe to log.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from typing import Any

_secret_cache: bytes | None = None


def _secret() -> bytes:
    """HMAC key for pseudonyms. Order: PII_TOKEN_SECRET (tests, local) -> Secrets Manager (PII_TOKEN_SECRET_ARN).
    With PII_REQUIRE_SECRET=1 (set in every deployed component) a missing secret is an error, never a weak default."""
    global _secret_cache
    if _secret_cache is not None:
        return _secret_cache
    value = os.environ.get("PII_TOKEN_SECRET")
    arn = os.environ.get("PII_TOKEN_SECRET_ARN")
    if not value and arn:
        import boto3  # lazy: keeps the module importable without AWS

        value = boto3.client("secretsmanager").get_secret_value(SecretId=arn)["SecretString"]
    if not value:
        if os.environ.get("PII_REQUIRE_SECRET") == "1":
            raise RuntimeError("PII token secret is not configured (PII_TOKEN_SECRET_ARN)")
        value = "dev-only-secret-change-me"
    _secret_cache = value.encode()
    return _secret_cache

NIK_RE = re.compile(r"(?<!\d)\d{16}(?!\d)")
NPWP_RE = re.compile(r"(?<!\d)\d{2}\.\d{3}\.\d{3}\.\d-\d{3}\.\d{3}(?!\d)")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_RE = re.compile(r"(?<!\d)(?:\+62|0)8\d{1,2}[-\s]?\d{3,4}[-\s]?\d{3,4}(?!\d)")
HONORIFIC_RE = re.compile(r"\b(Bapak|Ibu|Sdr\.?|Sdri\.?|Pak|Bu|Mr\.?|Ms\.?|Mrs\.?)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,2})")

# Ordered: more specific first so a 16-digit NIK is not mistaken for something else
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("NIK", NIK_RE), ("NPWP", NPWP_RE), ("EMAIL", EMAIL_RE), ("PHONE", PHONE_RE),
]

# Structured-record policy: key (lowercase) -> strategy
SENSITIVE_KEYS: dict[str, str] = {
    "nik": "tokenize", "ktp": "tokenize", "npwp": "tokenize",
    "name": "pseudonym", "employee_name": "pseudonym", "nama": "pseudonym", "full_name": "pseudonym",
    "phone": "redact", "email": "redact", "address": "redact", "alamat": "redact",
    "salary": "band_salary", "gaji": "band_salary", "base_salary": "band_salary",
    "dob": "age_band", "birth_date": "age_band", "date_of_birth": "age_band", "tanggal_lahir": "age_band",
    "health_condition": "category", "incident_detail": "category",
}

CLASSIFICATION: dict[str, tuple[str, str]] = {
    # key -> (sensitivity label, UU PDP category)
    "nik": ("Restricted", "identifier"), "npwp": ("Restricted", "identifier"),
    "name": ("Restricted", "general personal data"), "salary": ("Restricted", "specific (financial)"),
    "health_condition": ("Restricted", "specific (health)"), "incident_detail": ("Restricted", "specific (health)"),
    "dob": ("Confidential", "general personal data"), "phone": ("Confidential", "contact"),
    "email": ("Confidential", "contact"), "gender": ("Internal", "general personal data"),
}


def token(kind: str, value: str, n: int = 4) -> str:
    digest = hmac.new(_secret(), f"{kind}:{value}".encode(), hashlib.sha256).hexdigest().upper()
    return f"{kind}_{digest[:n]}"


def mask_text(text: str, mode: str = "tokenize", roster: list[str] | None = None) -> tuple[str, list[dict[str, Any]]]:
    """Mask PII inside free text. Returns (masked_text, findings)."""
    if not isinstance(text, str) or not text:
        return text, []
    findings: list[dict[str, Any]] = []
    out = text

    def _sub(kind: str):
        def repl(m: re.Match[str]) -> str:
            findings.append({"type": kind, "length": len(m.group(0))})
            return f"[{token(kind, m.group(0))}]" if mode == "tokenize" else "[REDACTED]"
        return repl

    for kind, rx in _PATTERNS:
        out = rx.sub(_sub(kind), out)
    for name in sorted(roster or [], key=len, reverse=True):
        if name and name in out:
            out = re.sub(re.escape(name), _sub("PERSON"), out)

    def _honorific(m: re.Match[str]) -> str:
        findings.append({"type": "PERSON", "length": len(m.group(2))})
        t = f"[{token('PERSON', m.group(2))}]" if mode == "tokenize" else "[REDACTED]"
        return f"{m.group(1)} {t}"

    out = HONORIFIC_RE.sub(_honorific, out)
    return out, findings


def _band_salary(v: Any) -> str:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return "[REDACTED]"
    lo = int(n // 10_000_000) * 10
    return f"IDR {lo}-{lo + 10}M"


def _age_band(v: Any, ref_year: int = 2025) -> str:
    m = re.match(r"(\d{4})", str(v))
    if not m:
        return "[REDACTED]"
    age = ref_year - int(m.group(1))
    lo = (age // 10) * 10
    return f"{lo}-{lo + 9}"


def _apply_strategy(strategy: str, key: str, value: Any, mode: str) -> Any:
    if strategy == "tokenize":
        return token(key.upper(), str(value)) if mode == "tokenize" else "[REDACTED]"
    if strategy == "pseudonym":
        return token("PERSON", str(value)) if mode == "tokenize" else "[REDACTED]"
    if strategy == "band_salary":
        return _band_salary(value)
    if strategy == "age_band":
        return _age_band(value)
    if strategy == "category":
        s = str(value).lower()
        return "None" if s in ("", "none", "tidak ada") else "Health event"
    return "[REDACTED]"


def mask_payload(obj: Any, mode: str = "tokenize", roster: list[str] | None = None,
                 _report: dict[str, int] | None = None) -> tuple[Any, dict[str, int]]:
    """Recursively mask dict/list/str structures. Returns (masked, {type: count})."""
    report = _report if _report is not None else {}
    if isinstance(obj, dict):
        res = {}
        for k, v in obj.items():
            strat = SENSITIVE_KEYS.get(str(k).lower())
            if strat and v not in (None, ""):
                res[k] = _apply_strategy(strat, str(k).lower(), v, mode)
                report[f"field:{str(k).lower()}"] = report.get(f"field:{str(k).lower()}", 0) + 1
            else:
                res[k], _ = mask_payload(v, mode, roster, report)
        return res, report
    if isinstance(obj, list):
        return [mask_payload(x, mode, roster, report)[0] for x in obj], report
    if isinstance(obj, str):
        masked, found = mask_text(obj, mode, roster)
        for f in found:
            report[f["type"]] = report.get(f["type"], 0) + 1
        return masked, report
    return obj, report


def classify_columns(columns: list[str]) -> list[dict[str, str]]:
    out = []
    for c in columns:
        label, cat = CLASSIFICATION.get(c.lower(), ("Internal", "non-personal"))
        strat = SENSITIVE_KEYS.get(c.lower(), "keep")
        out.append({"column": c, "sensitivity": label, "category": cat, "strategy": strat})
    return out


def guardrail_check(text: str, source: str = "INPUT") -> dict[str, Any]:
    """Second layer: Bedrock Guardrails ApplyGuardrail. No-op unless PII_GUARDRAIL_ID is configured."""
    gid = os.environ.get("PII_GUARDRAIL_ID")
    if not gid:
        return {"enabled": False}
    import boto3  # lazy: keeps the module importable in tests

    client = boto3.client("bedrock-runtime")
    resp = client.apply_guardrail(
        guardrailIdentifier=gid,
        guardrailVersion=os.environ.get("PII_GUARDRAIL_VERSION", "DRAFT"),
        source=source,
        content=[{"text": {"text": text}}],
    )
    return {"enabled": True, "action": resp.get("action"), "outputs": resp.get("outputs", [])}
