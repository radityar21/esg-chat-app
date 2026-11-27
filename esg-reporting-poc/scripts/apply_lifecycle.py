#!/usr/bin/env python3
"""Adds 14-day expiry rules for operational data in the existing output bucket WITHOUT touching other rules.

Expires: agent-ledger/, executions/, platform-cache/, etl-reports/, sections/ history is kept (it belongs to the reports).
Keeps:   generated reports, compliance/ attestations and alerts (state, not telemetry).
Rules created by this script have IDs starting with "esg-platform-"; re-running replaces only those.

    python scripts/apply_lifecycle.py [--bucket esg-output-reports-061039769766] [--days 14] [--dry-run]
"""
import argparse
import json

import boto3
from botocore.exceptions import ClientError

PREFIXES = ["agent-ledger/", "executions/", "platform-cache/", "etl-reports/"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bucket", default="esg-output-reports-061039769766")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    s3 = boto3.client("s3")
    try:
        rules = s3.get_bucket_lifecycle_configuration(Bucket=a.bucket)["Rules"]
    except ClientError as e:
        if e.response["Error"]["Code"] != "NoSuchLifecycleConfiguration":
            raise
        rules = []
    kept = [r for r in rules if not r["ID"].startswith("esg-platform-")]
    new = [{"ID": f"esg-platform-expire-{p.strip('/')}", "Status": "Enabled", "Filter": {"Prefix": p}, "Expiration": {"Days": a.days},
            "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1}} for p in PREFIXES]
    cfg = {"Rules": kept + new}
    print(json.dumps(cfg, indent=2))
    if not a.dry_run:
        s3.put_bucket_lifecycle_configuration(Bucket=a.bucket, LifecycleConfiguration=cfg)
        print(f"applied: {len(kept)} existing rule(s) kept, {len(new)} added")


if __name__ == "__main__":
    main()
