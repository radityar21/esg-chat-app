#!/usr/bin/env python3
"""Uploads the Knowledge Base documents (with their metadata), the prompts and the section templates, then starts ingestion.

    python scripts/upload_kb_documents.py --kb-id <KnowledgeBaseId> --data-source-id <KnowledgeBaseDataSourceId>
    python scripts/upload_kb_documents.py --skip-ingest          (upload only)

Documents go to s3://esg-kb-documents-<account>/documents/<category>/..., each with <file>.metadata.json (framework, category, ...)
which the report generator uses to filter retrieval. prompts/ and prompts/templates/ are read by the section generator.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import boto3

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import setup_kb_documents as kb  # noqa: E402  (the document catalogue lives there)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb-id")
    ap.add_argument("--data-source-id")
    ap.add_argument("--skip-ingest", action="store_true")
    ap.add_argument("--region", default="us-east-1")
    a = ap.parse_args()
    acct = boto3.client("sts").get_caller_identity()["Account"]
    bucket = f"esg-kb-documents-{acct}"
    s3 = boto3.client("s3", region_name=a.region)

    missing = [d["local_file"] for d in kb.DOCUMENTS if not d["local_file"].exists()]
    if missing:
        raise SystemExit("Missing source files:\n  " + "\n  ".join(str(m) for m in missing))
    for d in kb.DOCUMENTS:
        key = "documents/" + d["s3_key"]
        s3.upload_file(str(d["local_file"]), bucket, key)
        s3.put_object(Bucket=bucket, Key=key + ".metadata.json", Body=json.dumps({"metadataAttributes": d["metadata"]}).encode(), ContentType="application/json")
        print("uploaded", key)
    n = 0
    for folder, prefix in (("prompts", "prompts/"), ("templates", "prompts/templates/")):
        for f in sorted((ROOT / folder).glob("*.txt")):
            s3.upload_file(str(f), bucket, prefix + f.name)
            n += 1
    print(f"uploaded {n} prompt/template files")

    if a.skip_ingest:
        return
    if not (a.kb_id and a.data_source_id):
        raise SystemExit("Give --kb-id and --data-source-id to start ingestion (or use --skip-ingest).")
    agent = boto3.client("bedrock-agent", region_name=a.region)
    job = agent.start_ingestion_job(knowledgeBaseId=a.kb_id, dataSourceId=a.data_source_id)["ingestionJob"]["ingestionJobId"]
    print("ingestion job", job)
    while True:
        st = agent.get_ingestion_job(knowledgeBaseId=a.kb_id, dataSourceId=a.data_source_id, ingestionJobId=job)["ingestionJob"]
        print(" ", st["status"], st.get("statistics", ""))
        if st["status"] in ("COMPLETE", "FAILED", "STOPPED"):
            if st["status"] != "COMPLETE":
                raise SystemExit(f"ingestion {st['status']}: {st.get('failureReasons')}")
            break
        time.sleep(20)


if __name__ == "__main__":
    main()
