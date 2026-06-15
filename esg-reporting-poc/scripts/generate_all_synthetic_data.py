#!/usr/bin/env python3
# =============================================================================
# Run all synthetic data generators
# =============================================================================
# Generates all 3 datasets and optionally uploads to S3
#
# Usage:
#   python generate_all_synthetic_data.py              # Generate locally only
#   python generate_all_synthetic_data.py --upload     # Generate + upload to S3
# =============================================================================

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
SCRIPTS = [
    "generate_energy_data.py",
    "generate_loan_portfolio.py",
    "generate_hr_metrics.py",
]

S3_BUCKET = "esg-data-raw-061039769766"
S3_MAPPINGS = {
    "energy_consumption": "2024/energy/",
    "loan_portfolio": "2024/loans/",
    "hr_metrics": "2024/social/",
}


def run_generators():
    """Run all data generation scripts."""
    print("=" * 60)
    print("  RUNNING ALL SYNTHETIC DATA GENERATORS")
    print("=" * 60)

    for script in SCRIPTS:
        print(f"\n{'─' * 60}")
        print(f"  Running: {script}")
        print(f"{'─' * 60}\n")

        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / script)],
            capture_output=False,
        )
        if result.returncode != 0:
            print(f"\n❌ FAILED: {script}")
            sys.exit(1)

    print(f"\n{'=' * 60}")
    print("  ✅ ALL GENERATORS COMPLETED SUCCESSFULLY")
    print(f"{'=' * 60}")


def upload_to_s3():
    """Upload generated Parquet files to S3."""
    print(f"\n{'=' * 60}")
    print("  UPLOADING TO S3")
    print(f"{'=' * 60}")

    data_dir = SCRIPTS_DIR.parent / "data" / "synthetic"

    for dataset, s3_prefix in S3_MAPPINGS.items():
        local_path = data_dir / dataset
        if not local_path.exists():
            print(f"  ⚠️  {local_path} not found, skipping")
            continue

        s3_target = f"s3://{S3_BUCKET}/{s3_prefix}"
        print(f"\n  Uploading {dataset} → {s3_target}")

        # Upload all parquet files (including partitions)
        result = subprocess.run(
            ["aws", "s3", "cp", str(local_path), s3_target, "--recursive",
             "--exclude", "*.csv", "--include", "*.parquet"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"  ✅ {dataset} uploaded")
        else:
            print(f"  ❌ Upload failed: {result.stderr}")


if __name__ == "__main__":
    run_generators()

    if "--upload" in sys.argv:
        upload_to_s3()
    else:
        print("\n💡 Tip: Run with --upload to push to S3:")
        print(f"   python {Path(__file__).name} --upload")
