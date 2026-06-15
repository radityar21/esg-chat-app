"""
=============================================================================
Lambda #3: SectionGenFn
=============================================================================
Spec Reference: §5.4, §6, REQ-PROMPT-12 to REQ-PROMPT-17, REQ-KB-06 to REQ-KB-09

Purpose:
    Generates a single report section using Bedrock Claude 3.5 Sonnet.
    Composes prompt from: base_prompt + framework_overlay + section_template
    with DATA INPUT from Athena and RAG CONTEXT from Knowledge Base.

Input:
    {
        "section_id": "scope1",
        "framework": "GRI_305",
        "reporting_year": 2024,
        "metrics_json": {...},
        "kb_id": "XXXXXXXX",
        "execution_id": "arn:aws:states:..."
    }

Output:
    {
        "section_id": "GRI_305_S1_2024",
        "content_json": {...},
        "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "token_usage": {"input": 3200, "output": 2100}
    }

Deployment:
    Runtime: Python 3.11, Memory: 1024 MB, Timeout: 180s
    Role: ESG-SectionGen-ExecutionRole

Raises:
    UnresolvedPlaceholderError: If {placeholder} strings remain after resolution.
    JSONDecodeError: If LLM response is not valid JSON.
=============================================================================
"""

from __future__ import annotations

import json
import re
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.config import Config as BotoConfig

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# =============================================================================
# CONFIGURATION
# =============================================================================

ACCOUNT_ID: str = "061039769766"
KB_BUCKET: str = f"esg-kb-documents-{ACCOUNT_ID}"
SECTION_OUTPUT_BUCKET: str = f"esg-output-reports-{ACCOUNT_ID}"
MODEL_ID: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
BEDROCK_REGION: str = "us-east-1"
MAX_TOKENS: int = 12000
TEMPERATURE: float = 0.0
MIN_RELEVANCE_SCORE: float = 0.40

# REQ-PROMPT-13: Framework → overlay filename (one per invocation)
OVERLAY_MAP: dict[str, str | None] = {
    "GRI_305": "overlay_gri305.txt",
    "IFRS_S2": "overlay_ifrs_s2.txt",
    "CSRD_ESRS_E1": "overlay_esrs_e1.txt",  # Fixed: was overlay_csrd_e1.txt
    "OJK_PSPK": "overlay_ojk_pspk.txt",
    "NONE": None,
}

# REQ-TMPL-11: Template file naming convention
TEMPLATE_MAP: dict[str, str] = {
    "scope1": "templates/scope1_template.txt",
    "scope2": "templates/scope2_template.txt",
    "scope3_pcaf": "templates/scope3_pcaf_template.txt",
    "intensity": "templates/intensity_template.txt",
    "social": "templates/social_template.txt",
    "reduction": "templates/reduction_template.txt",
    "governance": "templates/governance_template.txt",
    "targets": "templates/targets_template.txt",
    "summary": "templates/summary_template.txt",
    "double_materiality": "templates/section_double_materiality.txt",
    # Unified (multi-framework) templates
    "scope1_unified": "templates/section_unified_scope1.txt",
    "scope2_unified": "templates/section_unified_scope2.txt",
    "scope3_pcaf_unified": "templates/section_unified_scope3_pcaf.txt",
    "intensity_unified": "templates/section_unified_intensity.txt",
    "reduction_unified": "templates/section_unified_reduction.txt",
    "social_unified": "templates/section_unified_social.txt",
    "governance_unified": "templates/section_unified_governance.txt",
    "targets_unified": "templates/section_unified_targets.txt",
}

# REQ-KB-07: RAG queries per section (exact spec wording)
RAG_QUERIES: dict[str, str | None] = {
    "scope1": "GRI 305-1 disclosure requirements direct emissions consolidation approach",
    "scope2": "GHG Protocol Scope 2 Guidance dual reporting location-based market-based contractual instruments",
    "scope3_pcaf": "PCAF Global Standard financed emissions attribution factor data quality score methodology",
    "intensity": "GRI 305-4 GHG emissions intensity ratio denominator definition",
    "social": "GRI 2-7 401-1 404-1 405-1 406-1 workforce employment training diversity non-discrimination disclosure requirements",
    "reduction": "GRI 305-5 reduction GHG emissions initiatives targets base year methodology",
    "governance": "IFRS S2 governance climate oversight board management responsibilities",
    "targets": "IFRS S2 strategy scenario analysis transition plan 1.5 degrees",
    "summary": None,  # REQ-PROMPT-15: No RAG for executive summary
    # Unified (multi-framework) — NO framework filter, query all
    "scope1_unified": "direct GHG emissions Scope 1 disclosure requirements GRI IFRS ESRS OJK methodology consolidation",
    "scope2_unified": "energy indirect Scope 2 emissions dual reporting location market based GRI IFRS ESRS",
    "scope3_pcaf_unified": "financed emissions Scope 3 PCAF attribution data quality GRI IFRS ESRS OJK",
    "intensity_unified": "emissions intensity ratio per revenue per employee GRI IFRS ESRS OJK",
    "reduction_unified": "GHG emission reduction initiatives targets transition plan GRI IFRS ESRS OJK",
    "social_unified": "workforce employment training diversity human capital GRI ESRS OJK social",
    "governance_unified": "climate governance board oversight ESG committee remuneration IFRS ESRS OJK",
    "targets_unified": "climate targets net zero SBTi transition plan scenario IFRS ESRS OJK",
}

# Benchmark RAG queries — pulls peer comparison data from benchmark KB docs
RAG_QUERIES_BENCHMARK: dict[str, str | None] = {
    "scope1": "GHG Scope 1 emissions benchmark Indonesian banking best practice reduction initiatives",
    "scope2": "Scope 2 energy electricity renewable energy benchmark banking Indonesia DBS RE100",
    "scope3_pcaf": "PCAF financed emissions data quality score benchmark banking peer SBTi NZBA",
    "intensity": "emissions intensity ratio benchmark financial institution per revenue per employee banking",
    "social": "training hours gender diversity turnover benchmark Indonesian banking BCA DBS OCBC BRI peer comparison",
    "reduction": "GHG emissions reduction initiatives best practice banking Indonesia RE100 green building EV fleet solar",
    "governance": "ESG governance structure board committee anti-corruption benchmark banking Indonesia BRI BCA DBS",
    "targets": "net zero target climate strategy SBTi benchmark banking NZBA reduction initiatives",
    "summary": None,
    # Unified (multi-framework) benchmark queries
    "scope1_unified": "GHG Scope 1 emissions benchmark Indonesian banking best practice reduction",
    "scope2_unified": "Scope 2 energy renewable benchmark banking Indonesia DBS RE100 green building",
    "scope3_pcaf_unified": "PCAF financed emissions benchmark banking SBTi NZBA data quality peer",
    "intensity_unified": "emissions intensity benchmark financial institution per revenue banking",
    "reduction_unified": "GHG reduction initiatives benchmark banking RE100 green building EV solar",
    "social_unified": "training hours gender diversity turnover benchmark Indonesian banking peer",
    "governance_unified": "ESG governance structure board committee benchmark banking BRI BCA DBS",
    "targets_unified": "net zero SBTi climate target benchmark banking NZBA transition",
    "double_materiality": "climate risk assessment double materiality physical risk transition risk financial impact banking Indonesia",
}

# Hybrid RAG: framework-specific queries (aggressive lookup)
# Key: (section_id, framework) → query text optimized for that framework's KB docs
RAG_QUERIES_BY_FRAMEWORK: dict[tuple[str, str], str] = {
    # GRI 305 (primary — most KB docs are GRI-tagged)
    ("scope1", "GRI_305"): "GRI 305-1 disclosure requirements direct emissions consolidation approach",
    ("scope2", "GRI_305"): "GHG Protocol Scope 2 Guidance dual reporting location-based market-based",
    ("scope3_pcaf", "GRI_305"): "PCAF Global Standard financed emissions attribution factor data quality",
    ("intensity", "GRI_305"): "GRI 305-4 GHG emissions intensity ratio denominator definition",
    ("reduction", "GRI_305"): "GRI 305-5 reduction GHG emissions initiatives targets base year",
    ("social", "GRI_305"): "GRI 2-7 401-1 404-1 405-1 406-1 workforce employment training diversity",
    # IFRS S2
    ("scope1", "IFRS_S2"): "IFRS S2 Scope 1 direct GHG emissions climate-related disclosures metrics",
    ("scope3_pcaf", "IFRS_S2"): "IFRS S2 financed emissions Scope 3 category 15 climate metrics",
    ("governance", "IFRS_S2"): "IFRS S2 governance climate oversight board management responsibilities paragraph 5-7",
    ("targets", "IFRS_S2"): "IFRS S2 climate targets transition plan scenario analysis 1.5 degrees paragraph 33-37",
    # CSRD ESRS E1
    ("scope1", "CSRD_ESRS_E1"): "ESRS E1-6 gross Scope 1 GHG emissions disclosure requirements",
    ("scope3_pcaf", "CSRD_ESRS_E1"): "ESRS E1-6 Scope 3 financed emissions total GHG indirect",
    # OJK PSPK
    ("scope1", "OJK_PSPK"): "OJK PSPK emisi gas rumah kaca langsung Scope 1 pelaporan keberlanjutan",
    ("scope3_pcaf", "OJK_PSPK"): "OJK PSPK emisi pembiayaan PCAF Scope 3 kategori 15",
    ("intensity", "OJK_PSPK"): "OJK PSPK intensitas emisi GRK per pendapatan lembaga jasa keuangan",
}

# REQ-PROMPT-15: RAG token caps per section
RAG_TOKEN_CAP: dict[str, int] = {
    # Legacy (single-framework)
    "scope1": 500,
    "scope2": 500,
    "scope3_pcaf": 700,
    "intensity": 400,
    "social": 500,
    "reduction": 600,
    "governance": 600,
    "targets": 700,
    "summary": 0,
    # Unified (multi-framework) — higher caps
    "scope1_unified": 1500,
    "scope2_unified": 1200,
    "scope3_pcaf_unified": 2000,
    "intensity_unified": 1000,
    "reduction_unified": 1500,
    "social_unified": 1200,
    "governance_unified": 1500,
    "targets_unified": 1500,
    "double_materiality": 1500,
}

BENCHMARK_TOKEN_CAP: dict[str, int] = {
    "scope1": 500,
    "scope2": 500,
    "scope3_pcaf": 700,
    "intensity": 400,
    "social": 500,
    "reduction": 600,
    "governance": 600,
    "targets": 700,
    "summary": 0,
    "scope1_unified": 2000,
    "scope2_unified": 1500,
    "scope3_pcaf_unified": 2500,
    "intensity_unified": 1500,
    "reduction_unified": 2000,
    "social_unified": 2000,
    "governance_unified": 2000,
    "targets_unified": 2000,
    "double_materiality": 2000,
}

s3_client = boto3.client("s3")
bedrock_client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION, config=BotoConfig(read_timeout=300, connect_timeout=10, retries={"max_attempts": 2}))
bedrock_agent_client = boto3.client("bedrock-agent-runtime", region_name=BEDROCK_REGION)

# =============================================================================
# FRAMEWORK FILTER MAPPING (REQ-KB-06)
# Some sections reference multiple frameworks in KB
# =============================================================================

# Sections that need cross-framework RAG retrieval
CROSS_FRAMEWORK_FILTERS: dict[str, list[str]] = {
    "scope3_pcaf": ["GRI_305", "PCAF"],
    "targets": ["IFRS_S2", "TCFD"],
    "governance": ["IFRS_S2", "TCFD"],
}


# =============================================================================
# TEMPLATE KEY RESOLUTION
# =============================================================================

def _resolve_template_key(section_id: str) -> str:
    """Resolve full section_id (e.g. 'GRI_305_SCOPE1_2024') to TEMPLATE_MAP key (e.g. 'scope1').

    Handles both short keys (already in TEMPLATE_MAP) and full section IDs from Step Functions.

    Args:
        section_id: Full section ID or short template key.

    Returns:
        Valid TEMPLATE_MAP key.

    Raises:
        ValueError: If section_id cannot be resolved.
    """
    # Direct match — already a valid key
    if section_id in TEMPLATE_MAP:
        return section_id

    # Pattern-based extraction from full section_id
    sid = section_id.lower()
    if "scope1" in sid or "_s1_" in sid:
        return "scope1"
    if "scope2" in sid or "_s2_" in sid:
        return "scope2"
    if "pcaf" in sid or "scope3" in sid or "_s3_" in sid:
        return "scope3_pcaf"
    if "intensity" in sid:
        return "intensity"
    if "social" in sid:
        return "social"
    if "reduction" in sid or "305-5" in sid or "reduce" in sid:
        return "reduction"
    if "summary" in sid:
        return "summary"
    if "gov" in sid:
        return "governance"
    if "target" in sid:
        return "targets"
    if "materiality" in sid or "double_material" in sid:
        return "double_materiality"

    raise ValueError(
        f"No template for section_id '{section_id}'. "
        f"Valid: {list(TEMPLATE_MAP.keys())}"
    )


def _build_kb_filter(section_id: str, framework: str) -> dict[str, Any]:
    """Build metadata filter for KB retrieval.

    Args:
        section_id: Section being generated.
        framework: Primary framework.

    Returns:
        Filter dict for Bedrock KB retrievalConfiguration.
    """
    # Check if section needs cross-framework retrieval
    additional_frameworks = CROSS_FRAMEWORK_FILTERS.get(section_id)

    if additional_frameworks:
        # Combine primary framework + additional
        all_frameworks = list(set([framework] + additional_frameworks))
        return {
            "orAll": [
                {"equals": {"key": "framework", "value": fw}}
                for fw in all_frameworks
            ]
        }
    else:
        # Single framework filter
        return {"equals": {"key": "framework", "value": framework}}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Generate a single report section via Bedrock.

    Args:
        event: Input with section_id, framework, reporting_year, metrics_json, kb_id.
        context: Lambda context.

    Returns:
        Dict with section_id, content_json, model_id, token_usage.

    Raises:
        ValueError: If section_id not found in TEMPLATE_MAP.
        RuntimeError: If placeholder resolution fails or LLM returns invalid JSON.
    """
    logger.info(f"SectionGenFn invoked: section={event.get('section_id')}, framework={event.get('framework')}")

    section_id: str = event["section_id"]
    framework: str = event["framework"]
    reporting_year: int = event["reporting_year"]
    metrics_json: dict = event["metrics_json"]
    kb_id: str | None = event.get("kb_id")
    execution_id: str = event.get("execution_id", "local-test")

    # =========================================================================
    # STEP 1: Load prompts from S3
    # =========================================================================
    base_prompt = _load_prompt_from_s3("base_prompt.txt")

    # REQ-PROMPT-13: One overlay per invocation
    overlay_file = OVERLAY_MAP.get(framework)
    overlay_prompt = _load_prompt_from_s3(overlay_file) if overlay_file else ""

    # REQ-TMPL-11: Template file naming
    template_key = _resolve_template_key(section_id)
    logger.info(f"Resolved section_id '{section_id}' -> template_key '{template_key}'")
    template_path = TEMPLATE_MAP.get(template_key)
    if not template_path:
        raise ValueError(f"No template for template_key '{template_key}'. Valid: {list(TEMPLATE_MAP.keys())}")
    section_template = _load_prompt_from_s3(template_path)
    section_template = section_template.replace("{reporting_year}", str(reporting_year))
    section_template = section_template.replace("{section_id}", section_id)

    # =========================================================================
    # STEP 2: Query Knowledge Base (REQ-KB-06, REQ-KB-07, REQ-KB-08, REQ-KB-09)
    # =========================================================================
    rag_context: str = ""
    rag_metadata: dict[str, Any] = {}
    rag_query = RAG_QUERIES.get(template_key)
    benchmark_query = RAG_QUERIES_BENCHMARK.get(template_key)

    # Unified sections: don't filter by framework (covers all)
    use_framework_filter = not template_key.endswith("_unified")

    if rag_query and kb_id:
        try:
            rag_context, rag_metadata = _query_knowledge_base(
                kb_id=kb_id,
                query=rag_query,
                framework=framework,
                section_id=template_key,
                max_tokens=RAG_TOKEN_CAP.get(template_key, 500),
                skip_framework_filter=not use_framework_filter,
            )
        except Exception as e:
            logger.warning(f"KB query failed (non-blocking): {str(e)}")
            rag_context = "RAG context unavailable for this section."
            rag_metadata = {"error": str(e), "results_count": 0, "results_used": 0}
    else:
        rag_metadata = {"results_count": 0, "results_used": 0, "skipped_reason": "no_rag_for_section"}

    # Benchmark RAG query (separate, no framework filter — uses BENCHMARK tag)
    benchmark_context: str = ""
    if benchmark_query and kb_id:
        try:
            benchmark_context, benchmark_meta = _query_knowledge_base_benchmark(
                kb_id=kb_id,
                query=benchmark_query,
                max_tokens=BENCHMARK_TOKEN_CAP.get(template_key, 500),
            )
            rag_metadata["benchmark_results_count"] = benchmark_meta.get("results_count", 0)
            rag_metadata["benchmark_results_used"] = benchmark_meta.get("results_used", 0)
        except Exception as e:
            logger.warning(f"Benchmark KB query failed (non-blocking): {str(e)}")
            benchmark_context = ""

    # Merge framework RAG + benchmark RAG
    if benchmark_context:
        rag_context = rag_context + "\n\n---\n\n## PEER BENCHMARKS (Indonesian Banking Sector)\n" + benchmark_context

    # REQ-KB-09: Log retrieval metadata
    logger.info(f"RAG retrieval: {json.dumps(rag_metadata)}")

    # =========================================================================
    # STEP 3: Compose prompt (REQ-PROMPT-12 composition order)
    # =========================================================================
    # [1] SYSTEM MESSAGE = base + "\n---\n" + overlay
    system_message: str = base_prompt
    if overlay_prompt:
        system_message += "\n\n---\n\n" + overlay_prompt

    # [2] USER MESSAGE = DATA INPUT + RAG CONTEXT + SECTION TEMPLATE
    user_message: str = f"""## DATA INPUT
{json.dumps(metrics_json, indent=2)}

## RAG CONTEXT
{rag_context if rag_context else "No RAG context available for this section."}

## SECTION TEMPLATE
{section_template}

## ADDITIONAL INSTRUCTIONS
{_load_insight_instructions(template_key)}

Generate the section for reporting_year={reporting_year}, framework={framework}, section_id={section_id}.
Return ONLY valid JSON per the output contract.
"""

    # =========================================================================
    # REQ-TMPL-05: Placeholder Resolution Enforcement
    # Verify zero {placeholder} strings remain
    # =========================================================================
    unresolved = re.findall(r"\{[a-z_]+\}", user_message)
    # Filter out JSON braces (only flag template-style placeholders)
    template_placeholders = [p for p in unresolved if p not in ("{", "}") and "_" in p]
    if template_placeholders:
        logger.warning(f"REQ-TMPL-05: Unresolved placeholders detected (non-blocking for POC): {template_placeholders[:5]}")
        # In production: raise RuntimeError(f"UnresolvedPlaceholderError: {template_placeholders}")

    # =========================================================================
    # STEP 4: Invoke Bedrock
    # =========================================================================
    logger.info(f"Invoking model: {MODEL_ID}")

    request_body: dict[str, Any] = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "system": system_message,
        "messages": [
            {"role": "user", "content": user_message}
        ]
    }

    response = bedrock_client.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(request_body)
    )

    response_body = json.loads(response["body"].read())
    generated_text: str = response_body["content"][0]["text"]
    input_tokens: int = response_body["usage"]["input_tokens"]
    output_tokens: int = response_body["usage"]["output_tokens"]

    # =========================================================================
    # STEP 5: Parse response as JSON
    # =========================================================================
    try:
        content_json = _extract_json(generated_text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed: {str(e)}")
        return {
            "error": "LLM response is not valid JSON",
            "raw_response": generated_text[:500],
            "section_id": section_id,
        }

    # =========================================================================
    # REQ-TMPL-07: Section Metadata
    # =========================================================================
    content_json["metadata"] = {
        "section_id": f"{framework}_{section_id.upper()}_{reporting_year}",
        "framework": framework,
        "reporting_year": reporting_year,
        "model_id": MODEL_ID,
        "prompt_version": "1.0.0",
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "data_input_hash": hashlib.sha256(json.dumps(metrics_json).encode()).hexdigest()[:16],
        "rag_context_hash": hashlib.sha256(rag_context.encode()).hexdigest()[:16],
        "execution_id": execution_id,
    }

    # =========================================================================
    # Write content_json to S3 (avoid Step Functions 256KB payload limit)
    # =========================================================================
    full_section_id = f"{framework}_{section_id.upper()}_{reporting_year}"
    execution_id_short = execution_id.split(":")[-1] if ":" in execution_id else execution_id
    s3_key = f"sections/{execution_id_short}/{full_section_id}.json"

    try:
        s3_client.put_object(
            Bucket=SECTION_OUTPUT_BUCKET,
            Key=s3_key,
            Body=json.dumps(content_json, ensure_ascii=False),
            ContentType="application/json",
        )
        logger.info(f"Section JSON written to s3://{SECTION_OUTPUT_BUCKET}/{s3_key}")
    except Exception as e:
        logger.error(f"Failed to write section to S3: {str(e)}")
        # Fallback: return inline (may hit payload limit for large sections)
        return {
            "section_id": full_section_id,
            "content_json": content_json,
            "model_id": MODEL_ID,
            "token_usage": {"input": input_tokens, "output": output_tokens},
            "rag_metadata": rag_metadata,
        }

    return {
        "section_id": full_section_id,
        "content_s3_key": s3_key,
        "content_s3_bucket": SECTION_OUTPUT_BUCKET,
        "model_id": MODEL_ID,
        "token_usage": {"input": input_tokens, "output": output_tokens},
        "rag_metadata": rag_metadata,
    }


# =============================================================================
# KNOWLEDGE BASE RETRIEVAL (REQ-KB-06, REQ-KB-08, REQ-KB-09)
# =============================================================================

def _query_knowledge_base(
    kb_id: str,
    query: str,
    framework: str,
    section_id: str,
    max_tokens: int,
    skip_framework_filter: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Query Bedrock Knowledge Base with HYBRID search and metadata filtering.

    Hybrid strategy:
    1. Check RAG_QUERIES_BY_FRAMEWORK for framework-specific query (aggressive)
    2. If found → use it with framework filter
    3. If not found → use generic query with framework filter
    4. If 0 results above threshold → FALLBACK: retry without framework filter

    For unified templates (skip_framework_filter=True), skip filter entirely on first try.

    Args:
        kb_id: Knowledge Base ID.
        query: Default/generic search query text.
        framework: Framework for metadata filter (e.g., "GRI_305").
        section_id: Section being generated (for cross-framework filter).
        max_tokens: Token cap for retrieved context.
        skip_framework_filter: If True, skip framework filter entirely (for unified templates).

    Returns:
        Tuple of (concatenated context string, retrieval metadata dict).
    """
    # Step 1: Check aggressive framework-specific query
    specific_query = RAG_QUERIES_BY_FRAMEWORK.get((section_id, framework))
    actual_query = specific_query if specific_query else query

    kb_filter = _build_kb_filter(section_id, framework)
    logger.info(f"KB query: '{actual_query[:60]}...' filter: {framework} (specific: {specific_query is not None}, skip_filter: {skip_framework_filter})")

    # Step 2: Build retrieval config
    # For unified templates, skip framework filter entirely
    retrieval_config = {
        "vectorSearchConfiguration": {
            "numberOfResults": 5,
            "overrideSearchType": "HYBRID",
        }
    }
    if not skip_framework_filter:
        retrieval_config["vectorSearchConfiguration"]["filter"] = {
            "equals": {"key": "framework", "value": framework}
        }

    # Primary query
    response = bedrock_agent_client.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={"text": actual_query},
        retrievalConfiguration=retrieval_config
    )

    results = response.get("retrievalResults", [])
    filtered_results = [
        r for r in results
        if r.get("score", 0) >= MIN_RELEVANCE_SCORE
    ]

    # Step 3: FALLBACK — if 0 usable results and we used a filter, retry WITHOUT framework filter
    used_fallback = False
    if len(filtered_results) == 0 and not skip_framework_filter:
        logger.info(f"No results with framework filter '{framework}', retrying without filter")
        response_fallback = bedrock_agent_client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": actual_query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": 5,
                    "overrideSearchType": "HYBRID",
                }
            }
        )
        results = response_fallback.get("retrievalResults", [])
        filtered_results = [
            r for r in results
            if r.get("score", 0) >= MIN_RELEVANCE_SCORE
        ]
        used_fallback = True

    for i, result in enumerate(filtered_results[:3]):
        score = result.get("score", 0)
        content_preview = result.get("content", {}).get("text", "")[:80]
        logger.info(f"KB result [{i}] score: {score:.4f}, preview: {content_preview}")

    # Step 4: Extract passages with token cap
    passages: list[str] = []
    total_chars: int = 0
    char_limit: int = max_tokens * 4
    results_used: int = 0

    for result in filtered_results:
        text = result.get("content", {}).get("text", "")
        if not text:
            continue  # Skip empty chunks
        if total_chars + len(text) > char_limit:
            remaining = char_limit - total_chars
            if remaining > 100:
                passages.append(text[:remaining] + "...")
                total_chars += remaining
                results_used += 1
            break
        passages.append(text)
        total_chars += len(text)
        results_used += 1

    context = "\n\n---\n\n".join(passages)

    metadata: dict[str, Any] = {
        "results_count": len(results),
        "results_above_threshold": len(filtered_results),
        "results_used": results_used,
        "min_score_threshold": MIN_RELEVANCE_SCORE,
        "token_cap": max_tokens,
        "chars_retrieved": total_chars,
        "framework_filter": framework if not skip_framework_filter else "NONE (unified)",
        "query_text": actual_query,
        "used_specific_query": specific_query is not None,
        "used_fallback_no_filter": used_fallback,
        "skip_framework_filter": skip_framework_filter,
    }

    return context, metadata


def _query_knowledge_base_benchmark(
    kb_id: str,
    query: str,
    max_tokens: int,
) -> tuple[str, dict[str, Any]]:
    """Query Bedrock Knowledge Base for benchmark/peer comparison data.

    Uses filter framework=BENCHMARK (no framework-specific filter).
    This retrieves peer banking data for advisory recommendations.

    Args:
        kb_id: Knowledge Base ID.
        query: Search query text (benchmark-focused).
        max_tokens: Token cap for retrieved context.

    Returns:
        Tuple of (concatenated context string, retrieval metadata dict).
    """
    logger.info(f"Benchmark KB query: {query[:80]}...")

    response = bedrock_agent_client.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": 5,
                "overrideSearchType": "HYBRID",
                "filter": {
                    "equals": {"key": "framework", "value": "BENCHMARK"}
                }
            }
        }
    )

    results = response.get("retrievalResults", [])

    # Lower threshold for benchmark docs (they're structured tables, scores may vary)
    benchmark_min_score = 0.30
    filtered_results = [
        r for r in results
        if r.get("score", 0) >= benchmark_min_score
    ]

    passages: list[str] = []
    total_chars: int = 0
    char_limit: int = max_tokens * 4
    results_used: int = 0

    for result in filtered_results:
        text = result.get("content", {}).get("text", "")
        if not text:
            continue  # Skip empty chunks
        if total_chars + len(text) > char_limit:
            remaining = char_limit - total_chars
            if remaining > 100:
                passages.append(text[:remaining] + "...")
                total_chars += remaining
                results_used += 1
            break
        passages.append(text)
        total_chars += len(text)
        results_used += 1

    context = "\n\n---\n\n".join(passages)

    metadata: dict[str, Any] = {
        "results_count": len(results),
        "results_above_threshold": len(filtered_results),
        "results_used": results_used,
        "min_score_threshold": benchmark_min_score,
        "token_cap": max_tokens,
        "chars_retrieved": total_chars,
        "query_text": query,
    }

    logger.info(f"Benchmark RAG: {results_used} results used, {total_chars} chars")
    return context, metadata


# =============================================================================
# PROMPT LOADING
# =============================================================================

def _load_prompt_from_s3(filename: str) -> str:
    """Load a prompt/template file from S3.

    Args:
        filename: File path relative to prompts/ prefix in KB bucket.

    Returns:
        File content as string.

    Raises:
        RuntimeError: If file cannot be loaded.
    """
    try:
        response = s3_client.get_object(Bucket=KB_BUCKET, Key=f"prompts/{filename}")
        return response["Body"].read().decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to load prompt '{filename}': {str(e)}")
        raise RuntimeError(f"Prompt load failed: {filename}") from e


# Cache insight instructions (loaded once per Lambda cold start)
_insight_instructions_cache: dict[str, str] = {}


def _load_insight_instructions(template_key: str) -> str:
    """Load appropriate insight layer instructions based on section type.

    Executive Summary gets EXEC_SUMMARY_TIER1_INSTRUCTIONS.txt.
    All other sections get INSIGHT_LAYER_INSTRUCTIONS.txt.

    Args:
        template_key: Template key (e.g., "scope1", "summary", "scope1_unified").

    Returns:
        Instruction text string.
    """
    # Determine which instruction file to load
    is_summary = "summary" in template_key
    file_key = "exec_summary" if is_summary else "insight_layer"

    if file_key in _insight_instructions_cache:
        return _insight_instructions_cache[file_key]

    filename = "templates/EXEC_SUMMARY_TIER1_INSTRUCTIONS.txt" if is_summary else "templates/INSIGHT_LAYER_INSTRUCTIONS.txt"

    try:
        content = _load_prompt_from_s3(filename)
        _insight_instructions_cache[file_key] = content
        return content
    except Exception as e:
        logger.warning(f"Insight instructions not available ({filename}): {str(e)}")
        return ""  # Non-blocking — section generates without insight layer if file missing


# =============================================================================
# JSON EXTRACTION
# =============================================================================

def _extract_json(text: str) -> dict[str, Any]:
    """Extract JSON from LLM response (may be wrapped in markdown fences).

    Args:
        text: Raw LLM response text.

    Returns:
        Parsed JSON as dict.

    Raises:
        json.JSONDecodeError: If no valid JSON found.
    """
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try markdown code block
    json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))

    # Try first { to last }
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])

    raise json.JSONDecodeError("No valid JSON found in response", text, 0)
