"""Chat history per user (the "hybrid" design).

DynamoDB (this module) keeps what the UI shows: the list of conversations and a readable transcript.
AgentCore Memory (in the runtime) keeps the agent's own working context, so a conversation continues with full context
even after the runtime session has ended.

Table layout (one table, partition key "user" = Cognito sub, sort key "sk"):
    conv#<conversation id>             title, created_at, updated_at, ttl
    msg#<conversation id>#<epoch ms>-<token>-<0 user | 1 assistant>   role, text, ttl
Everything expires 14 days after the last activity (TTL). Prompts are stored after PII masking.
"""

from __future__ import annotations

import os
import re
import time
import uuid
from typing import Any

from . import common

try:
    from pii_guard import mask_text
except ImportError:  # pragma: no cover
    from _shared.pii_guard import mask_text  # type: ignore

TABLE = os.environ.get("CONVERSATIONS_TABLE", "")
TTL_DAYS = int(os.environ.get("CONVERSATION_TTL_DAYS", "14"))
CONV_ID = re.compile(r"^[A-Za-z0-9_\-]{33,100}$")
MAX_TEXT = 20000


def _table():
    import boto3

    return boto3.resource("dynamodb", region_name=common.REGION).Table(TABLE)


def _ttl() -> int:
    return int(time.time()) + TTL_DAYS * 86400


def _title(prompt: str) -> str:
    t = re.sub(r"\s+", " ", prompt).strip()
    return t[:70] + ("…" if len(t) > 70 else "")


def record_turn(user: str, conv_id: str, prompt: str, answer: str, table: Any = None) -> None:
    """Store one question and answer. Called by the chat worker after the agent answered."""
    if not CONV_ID.match(conv_id or "") or not user:
        return
    t = table or _table()
    now_ms = int(time.time() * 1000)
    masked, _ = mask_text(prompt)
    ttl = _ttl()
    head = t.get_item(Key={"user": user, "sk": f"conv#{conv_id}"}).get("Item")
    t.put_item(Item={"user": user, "sk": f"conv#{conv_id}", "title": (head or {}).get("title") or _title(masked),
                     "created_at": (head or {}).get("created_at") or now_ms, "updated_at": now_ms, "ttl": ttl})
    tok = uuid.uuid4().hex[:6]  # two turns in the same millisecond must not overwrite each other
    t.put_item(Item={"user": user, "sk": f"msg#{conv_id}#{now_ms:015d}-{tok}-0", "role": "user", "text": masked[:MAX_TEXT], "ttl": ttl})
    t.put_item(Item={"user": user, "sk": f"msg#{conv_id}#{now_ms:015d}-{tok}-1", "role": "assistant", "text": str(answer)[:MAX_TEXT], "ttl": ttl})


def _query(t: Any, user: str, prefix: str) -> list[dict[str, Any]]:
    from boto3.dynamodb.conditions import Key

    items, kw = [], {"KeyConditionExpression": Key("user").eq(user) & Key("sk").begins_with(prefix)}
    while True:
        r = t.query(**kw)
        items += r.get("Items", [])
        if "LastEvaluatedKey" not in r:
            return items
        kw["ExclusiveStartKey"] = r["LastEvaluatedKey"]


def list_conversations(user: str, table: Any = None) -> dict[str, Any]:
    t = table or _table()
    items = _query(t, user, "conv#")
    convs = [{"id": i["sk"][5:], "title": i.get("title", ""), "updated_at": int(i.get("updated_at", 0)), "created_at": int(i.get("created_at", 0))}
             for i in items]
    return {"conversations": sorted(convs, key=lambda c: -c["updated_at"])[:50], "retention_days": TTL_DAYS}


def get_conversation(user: str, conv_id: str, table: Any = None) -> dict[str, Any]:
    if not CONV_ID.match(conv_id or ""):
        raise ValueError("invalid conversation id")
    t = table or _table()
    head = t.get_item(Key={"user": user, "sk": f"conv#{conv_id}"}).get("Item")
    if not head:
        return {"found": False}
    msgs = sorted(_query(t, user, f"msg#{conv_id}#"), key=lambda m: m["sk"])
    return {"found": True, "id": conv_id, "title": head.get("title", ""),
            "messages": [{"role": m["role"], "text": m.get("text", ""), "at": int(m["sk"].rsplit("#", 1)[1][:15])} for m in msgs]}


def delete_conversation(user: str, conv_id: str, table: Any = None) -> dict[str, Any]:
    if not CONV_ID.match(conv_id or ""):
        raise ValueError("invalid conversation id")
    t = table or _table()
    keys = [{"user": user, "sk": f"conv#{conv_id}"}] + [{"user": user, "sk": m["sk"]} for m in _query(t, user, f"msg#{conv_id}#")]
    for k in keys:
        t.delete_item(Key=k)
    return {"deleted": conv_id, "items": len(keys)}
