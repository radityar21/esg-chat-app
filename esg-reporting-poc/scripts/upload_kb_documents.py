#!/usr/bin/env python3
"""Uploads the Knowledge Base documents (with their metadata), the prompts and the section templates, then starts ingestion.

    python scripts/upload_kb_documents.py --kb-id <KnowledgeBaseId> --data-source-id <KnowledgeBaseDataSourceId>
    python scripts/upload_kb_documents.py --skip-ingest          (upload only)

Documents go to s3://esg-kb-documents-<account>/documents/<category>/..., each with <file>.metadata.json (framework, category, ...)
which the report generator uses to filter retrieval. prompts/ and prompts/templates/ are read by the section generator.

Semantic chunking accepts at most 1,000,000 characters of text per file. PDFs above MAX_CHARS are split into page ranges
(<name>_part1.pdf, ...) with the same metadata, and the unsplit object is removed from S3. Needs: pip install pypdf
Re-running is safe: ingestion only processes new or changed files.
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

MAX_CHARS = 800_000  # margin below the 1,000,000 character limit of semantic chunking


def split_pdf(path: Path) -> list[tuple[str, bytes]]:
    """Return [(suffix, pdf_bytes)]. One item with suffix '' when the file is small enough."""
    import io
    import logging

    from pypdf import PdfReader, PdfWriter

    logging.getLogger("pypdf").setLevel(logging.ERROR)  # font-encoding warnings are irrelevant for text length

    reader = PdfReader(str(path))
    sizes = [len(p.extract_text() or "") for p in reader.pages]
    if sum(sizes) <= MAX_CHARS:
        return [("", path.read_bytes())]
    parts, start, acc = [], 0, 0
    for i, n in enumerate(sizes):
        if acc + n > MAX_CHARS and i > start:
            parts.append((start, i))
            start, acc = i, 0
        acc += n
    parts.append((start, len(sizes)))
    out = []
    for k, (a, b) in enumerate(parts, 1):
        w = PdfWriter()
        for i in range(a, b):
            w.add_page(reader.pages[i])
        buf = io.BytesIO()
        w.write(buf)
        out.append((f"_part{k}", buf.getvalue()))
    print(f"  split {path.name}: {sum(sizes):,} characters -> {len(out)} parts")
    return out


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
        meta = json.dumps({"metadataAttributes": d["metadata"]}).encode()
        parts = split_pdf(d["local_file"]) if key.lower().endswith(".pdf") else [("", d["local_file"].read_bytes())]
        if len(parts) > 1:
            s3.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": key}, {"Key": key + ".metadata.json"}], "Quiet": True})
        for suffix, body in parts:
            k = key[:-4] + suffix + key[-4:] if suffix else key
            s3.put_object(Bucket=bucket, Key=k, Body=body)
            s3.put_object(Bucket=bucket, Key=k + ".metadata.json", Body=meta, ContentType="application/json")
            print("uploaded", k)
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
