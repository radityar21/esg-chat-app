"""The report catalog is the single source of the report structure; the generator and the planner must agree with it."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "lambda" / "_shared"), str(ROOT / "agentcore")]
import report_catalog as C  # noqa: E402


def test_every_template_file_exists_in_the_repository():
    missing = [s["file"] for s in C.SECTIONS.values() if not (ROOT / "templates" / s["file"]).exists()]
    assert missing == []


def test_section_generator_fallback_map_matches_the_catalog():
    import importlib.util
    import os
    os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
    spec = importlib.util.spec_from_file_location("section_gen_handler", ROOT / "lambda" / "section_gen" / "handler.py")
    sg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sg)
    assert {k: v.split("/", 1)[1] for k, v in sg.TEMPLATE_MAP.items()} == {k: s["file"] for k, s in C.SECTIONS.items()}
    assert "Bahasa Indonesia" in sg._language_block("id") and sg._language_block("en") == ""


def test_every_framework_section_is_in_the_catalog():
    for fw, f in C.FRAMEWORKS.items():
        assert all(s in C.SECTIONS for s in f["sections"]), fw


def test_section_subset_keeps_framework_order_and_language():
    t = C.section_templates("IFRS_S2", ["social", "scope1", "summary"], "id")
    assert [x["template_id"] for x in t] == ["summary", "scope1", "social"]
    assert all(x["language"] == "id" for x in t) and t[0]["framework"] == "IFRS_S2"
    assert C.section_templates("GRI_305")[0] == {"template_id": "summary", "framework": "NONE", "language": "en"}


@pytest.mark.parametrize("args", [("XYZ", None, "en"), ("GRI_305", ["governance"], "en"), ("GRI_305", None, "fr")])
def test_bad_report_requests_are_rejected(args):
    with pytest.raises(ValueError):
        C.section_templates(*args)


def test_planner_builds_language_and_subset_into_the_pipeline_input():
    from orchestrator.config import Settings
    from orchestrator.pipelines import SECTION_TEMPLATES, build_input
    s = Settings(output_bucket="b", report_state_machine_arn="arn:x")
    inp = build_input("esg_report", {"reporting_year": 2024, "framework": "OJK_PSPK", "language": "id", "sections": ["scope1", "scope2"]}, s)
    assert inp["language"] == "id" and [t["template_id"] for t in inp["section_templates"]] == ["scope1", "scope2"]
    default = build_input("esg_report", {"reporting_year": 2024, "framework": "GRI_305"}, s)
    assert default["language"] == "en" and len(default["section_templates"]) == 7
    assert [t["template_id"] for t in SECTION_TEMPLATES["MULTI_FRAMEWORK"]][-1] == "summary"
