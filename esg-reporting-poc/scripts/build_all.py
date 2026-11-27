#!/usr/bin/env python3
"""Prepares every artifact the CDK stacks need. Run once before the first `cdk deploy`, and again after changing code.

    python scripts/build_all.py            (from esg-reporting-poc/, works on Windows, no Docker)

Creates under build/:
    lambda-stage/<fn>/      pipeline Lambda code, with the shared modules flat next to handler.py
    docxlayer/python/       python-docx for Lambda (Linux x86_64, Python 3.12)
    layer/python/           recent boto3 (the platform Lambda needs the bedrock-agentcore client)
    pglayer/python/         pg8000 for the Lambdas inside the VPC
    agent.zip               AgentCore Runtime code package (Linux arm64)
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
PIPELINE = ["validate_input", "athena_query", "section_gen", "validation", "filter_sections", "assembly_doc"]


def pip(target: Path, *args: str) -> None:
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", "--target", str(target), *args], check=True)


def stage_lambdas() -> None:
    stage = BUILD / "lambda-stage"
    shutil.rmtree(stage, ignore_errors=True)
    for fn in PIPELINE:
        d = stage / fn
        d.mkdir(parents=True)
        shutil.copy2(ROOT / "lambda" / fn / "handler.py", d / "handler.py")
        for f in (ROOT / "lambda" / "_shared").glob("*.py"):  # handlers import the shared modules as top-level modules
            shutil.copy2(f, d / f.name)
    print(f"staged {len(PIPELINE)} Lambda packages")


def main() -> None:
    BUILD.mkdir(exist_ok=True)
    stage_lambdas()
    pip(BUILD / "docxlayer" / "python", "--platform", "manylinux2014_x86_64", "--implementation", "cp", "--python-version", "3.12",
        "--only-binary=:all:", "python-docx>=1.1.0")
    print("docx layer ready")
    pip(BUILD / "layer" / "python", "boto3>=1.40")
    print("boto3 layer ready")
    pip(BUILD / "pglayer" / "python", "pg8000>=1.31", "python-dateutil<3")
    print("pg layer ready")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_agent_zip.py")], check=True)
    print("all artifacts ready")


if __name__ == "__main__":
    main()
