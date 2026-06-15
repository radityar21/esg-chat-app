#!/usr/bin/env python3
"""
=============================================================================
Setup Bedrock Knowledge Base Documents
=============================================================================
Creates metadata JSON files and generates upload commands for S3.

Run from: bedrock-agentcore-solution\ directory
Output: 
  1. Creates metadata JSON files alongside source docs
  2. Prints aws s3 cp commands to copy-paste into CMD

S3 Target: s3://esg-kb-documents-061039769766/
Structure per REQ-KB-11, REQ-KB-12
=============================================================================
"""

import json
from pathlib import Path

# =============================================================================
# CONFIG
# =============================================================================
BUCKET = "esg-kb-documents-061039769766"
BASE_DIR = Path(__file__).parent.parent.parent  # bedrock-agentcore-solution/

DOCS_DIR = BASE_DIR / "ESG Document" / "Critical" / "Complete version"
SAMPLE_DIR = BASE_DIR / "ESG Document" / "Important" / "Sample ESG Reports Redacted"

# Output dir for metadata files
META_OUTPUT_DIR = BASE_DIR / "esg-reporting-poc" / "data" / "kb_metadata"
META_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# DOCUMENT MAPPING: local file → S3 category/filename + metadata
# =============================================================================

DOCUMENTS = [
    # --- GRI ---
    {
        "local_file": DOCS_DIR / "01. GRI 305 Emissions 2016.pdf",
        "s3_key": "gri/GRI_305_Emissions_2016.pdf",
        "metadata": {
            "category": "gri",
            "framework": "GRI_305",
            "version": "2016",
            "effective_date": "2016-01-01",
            "document_title": "GRI 305: Emissions 2016",
            "language": "en",
            "contains_numeric_data": False
        }
    },
    {
        "local_file": DOCS_DIR / "GRI 1 Foundation 2021.pdf",
        "s3_key": "gri/GRI_1_Foundation_2021.pdf",
        "metadata": {
            "category": "gri",
            "framework": "GRI_1",
            "version": "2021",
            "effective_date": "2021-01-01",
            "document_title": "GRI 1: Foundation 2021",
            "language": "en",
            "contains_numeric_data": False
        }
    },

    # --- IFRS ---
    {
        "local_file": DOCS_DIR / "03. IFRS S2 Climate-related Disclosures-June 2023_Main Standard (Para 1-37).pdf",
        "s3_key": "ifrs/IFRS_S2_Climate_Disclosures_2023.pdf",
        "metadata": {
            "category": "ifrs",
            "framework": "IFRS_S2",
            "version": "2023",
            "effective_date": "2023-06-01",
            "document_title": "IFRS S2 Climate-related Disclosures (June 2023) - Main Standard",
            "language": "en",
            "contains_numeric_data": False
        }
    },
    {
        "local_file": DOCS_DIR / "03. IFRS S2 Climate-related Disclosures-June 2023_Industry Guidance (SASB FN-CB-410a).pdf",
        "s3_key": "ifrs/IFRS_S2_SASB_FN_CB_410a_Guidance.pdf",
        "metadata": {
            "category": "ifrs",
            "framework": "IFRS_S2",
            "version": "2023",
            "effective_date": "2023-06-01",
            "document_title": "IFRS S2 Industry Guidance - SASB FN-CB-410a",
            "language": "en",
            "contains_numeric_data": False
        }
    },

    # --- CSRD/ESRS ---
    {
        "local_file": DOCS_DIR / "05. ESRS E1 Climate Change (2023).pdf",
        "s3_key": "csrd/ESRS_E1_Climate_Change_2023.pdf",
        "metadata": {
            "category": "csrd",
            "framework": "CSRD_ESRS_E1",
            "version": "2023",
            "effective_date": "2023-01-01",
            "document_title": "ESRS E1: Climate Change (2023)",
            "language": "en",
            "contains_numeric_data": False
        }
    },

    # --- OJK ---
    {
        "local_file": DOCS_DIR / "08. POJK 51 2017 - keuangan berkelanjutan.pdf",
        "s3_key": "ojk/POJK_51_2017_Sustainable_Finance.pdf",
        "metadata": {
            "category": "ojk",
            "framework": "OJK_PSPK",
            "version": "2017",
            "effective_date": "2017-07-27",
            "document_title": "POJK No. 51/POJK.03/2017 tentang Penerapan Keuangan Berkelanjutan",
            "language": "id",
            "contains_numeric_data": False
        }
    },

    # --- GHG Methodology ---
    {
        "local_file": DOCS_DIR / "10. GHG Protocol Corporate Standard v2015.pdf",
        "s3_key": "ghg_methodology/GHG_Protocol_Corporate_Standard_v2015.pdf",
        "metadata": {
            "category": "ghg_methodology",
            "framework": "GHG_PROTOCOL",
            "version": "2015",
            "effective_date": "2015-01-01",
            "document_title": "GHG Protocol Corporate Accounting and Reporting Standard (Revised 2015)",
            "language": "en",
            "contains_numeric_data": False
        }
    },
    {
        "local_file": DOCS_DIR / "11. PCAF Global GHG Accounting Standard — Part A (2022).pdf",
        "s3_key": "ghg_methodology/PCAF_Standard_Part_A_2022.pdf",
        "metadata": {
            "category": "ghg_methodology",
            "framework": "PCAF",
            "version": "2022",
            "effective_date": "2022-01-01",
            "document_title": "PCAF Global GHG Accounting and Reporting Standard - Part A (2022)",
            "language": "en",
            "contains_numeric_data": False
        }
    },
    {
        "local_file": DOCS_DIR / "12. IPCC_AR6_WGI_Chapter_07.pdf",
        "s3_key": "ghg_methodology/IPCC_AR6_Chapter7_GWP.pdf",
        "metadata": {
            "category": "ghg_methodology",
            "framework": "IPCC",
            "version": "2021",
            "effective_date": "2021-08-09",
            "document_title": "IPCC AR6 WGI Chapter 7 - The Earth's Energy Budget",
            "language": "en",
            "contains_numeric_data": False
        }
    },

    # --- Style Reference (TXT files, redacted) ---
    {
        "local_file": SAMPLE_DIR / "BCA-EN-2025_REDACTED.txt",
        "s3_key": "style_reference/sample_esg_report_BCA_2025.txt",
        "metadata": {
            "category": "style_reference",
            "framework": "MULTI",
            "version": "2025",
            "effective_date": "2025-01-01",
            "document_title": "Sample ESG Report - BCA (Redacted)",
            "language": "en",
            "contains_numeric_data": False
        }
    },
    {
        "local_file": SAMPLE_DIR / "BRI-EN-2023_REDACTED.txt",
        "s3_key": "style_reference/sample_esg_report_BRI_2023.txt",
        "metadata": {
            "category": "style_reference",
            "framework": "MULTI",
            "version": "2023",
            "effective_date": "2023-01-01",
            "document_title": "Sample ESG Report - BRI (Redacted)",
            "language": "en",
            "contains_numeric_data": False
        }
    },
    {
        "local_file": SAMPLE_DIR / "DBS-EN-2023_REDACTED.txt",
        "s3_key": "style_reference/sample_esg_report_DBS_2023.txt",
        "metadata": {
            "category": "style_reference",
            "framework": "MULTI",
            "version": "2023",
            "effective_date": "2023-01-01",
            "document_title": "Sample ESG Report - DBS (Redacted)",
            "language": "en",
            "contains_numeric_data": False
        }
    },
    {
        "local_file": SAMPLE_DIR / "Mandiri-IND-2023_REDACTED.txt",
        "s3_key": "style_reference/sample_esg_report_Mandiri_2023.txt",
        "metadata": {
            "category": "style_reference",
            "framework": "MULTI",
            "version": "2023",
            "effective_date": "2023-01-01",
            "document_title": "Sample ESG Report - Mandiri (Redacted)",
            "language": "id",
            "contains_numeric_data": False
        }
    },
    {
        "local_file": SAMPLE_DIR / "OCBC-IND-2024_REDACTED.txt",
        "s3_key": "style_reference/sample_esg_report_OCBC_2024.txt",
        "metadata": {
            "category": "style_reference",
            "framework": "MULTI",
            "version": "2024",
            "effective_date": "2024-01-01",
            "document_title": "Sample ESG Report - OCBC (Redacted)",
            "language": "id",
            "contains_numeric_data": False
        }
    },
]


def main():
    print("=" * 70)
    print("  KB Document Setup — Metadata Generation + Upload Commands")
    print("=" * 70)

    # Step 1: Create metadata JSON files
    print("\n--- Creating metadata JSON files ---\n")
    metadata_files = []

    for doc in DOCUMENTS:
        meta_filename = doc["s3_key"] + ".metadata.json"
        meta_local_path = META_OUTPUT_DIR / meta_filename.replace("/", "_")

        meta_content = {"metadataAttributes": doc["metadata"]}

        meta_local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_local_path, "w", encoding="utf-8") as f:
            json.dump(meta_content, f, indent=2)

        metadata_files.append({
            "local_path": meta_local_path,
            "s3_key": meta_filename
        })
        print(f"  Created: {meta_local_path.name}")

    # Step 2: Verify all source files exist
    print("\n--- Checking source files ---\n")
    missing = []
    for doc in DOCUMENTS:
        if doc["local_file"].exists():
            print(f"  ✅ {doc['local_file'].name}")
        else:
            print(f"  ❌ MISSING: {doc['local_file']}")
            missing.append(doc["local_file"])

    if missing:
        print(f"\n⚠️  {len(missing)} files missing! Fix before uploading.")

    # Step 3: Generate CMD commands
    print("\n" + "=" * 70)
    print("  COPY-PASTE THESE COMMANDS (run from bedrock-agentcore-solution\\)")
    print("=" * 70)

    print("\nREM === Upload documents to S3 ===\n")

    for doc in DOCUMENTS:
        local = doc["local_file"]
        s3_target = f"s3://{BUCKET}/{doc['s3_key']}"
        # Use relative path from bedrock-agentcore-solution\
        try:
            rel_path = local.relative_to(BASE_DIR)
        except ValueError:
            rel_path = local
        print(f'aws s3 cp "{rel_path}" {s3_target}')

    print("\nREM === Upload metadata JSON files ===\n")

    for meta in metadata_files:
        local = meta["local_path"]
        s3_target = f"s3://{BUCKET}/{meta['s3_key']}"
        try:
            rel_path = local.relative_to(BASE_DIR)
        except ValueError:
            rel_path = local
        print(f'aws s3 cp "{rel_path}" {s3_target}')

    print(f"\nREM === Verify ===")
    print(f"aws s3 ls s3://{BUCKET}/ --recursive --summarize")

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  Total documents: {len(DOCUMENTS)}")
    print(f"  Total metadata files: {len(metadata_files)}")
    print(f"  Total S3 objects: {len(DOCUMENTS) + len(metadata_files)}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
