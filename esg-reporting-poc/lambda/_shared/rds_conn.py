"""PostgreSQL access for the Lambdas that live in the VPC (seed loader, read-only data tools).

Connection settings come from the environment (DB_HOST, DB_PORT, DB_NAME) and the credentials from Secrets Manager
(the secret JSON has ``username`` and ``password``). TLS is always on and verified against the RDS CA bundle that ships
next to this file.
"""

from __future__ import annotations

import json
import os
import ssl
from pathlib import Path
from typing import Any

CA = Path(__file__).with_name("rds-ca.pem")
_secrets: dict[str, dict[str, Any]] = {}


def _secret(arn: str) -> dict[str, Any]:
    if arn not in _secrets:
        import boto3

        _secrets[arn] = json.loads(boto3.client("secretsmanager").get_secret_value(SecretId=arn)["SecretString"])
    return _secrets[arn]


def connect(secret_arn: str):
    import pg8000.native

    s = _secret(secret_arn)
    ctx = ssl.create_default_context(cafile=str(CA))
    return pg8000.native.Connection(user=s["username"], password=s["password"], host=os.environ["DB_HOST"], port=int(os.environ.get("DB_PORT", "5432")),
                                    database=os.environ.get("DB_NAME", "esgdb"), ssl_context=ctx, timeout=15)


def rows(conn: Any, sql: str, **params: Any) -> list[dict[str, Any]]:
    out = conn.run(sql, **params)
    cols = [c["name"] for c in conn.columns or []]
    return [dict(zip(cols, r)) for r in (out or [])]
