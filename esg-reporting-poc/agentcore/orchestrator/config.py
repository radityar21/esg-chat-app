"""Runtime configuration for the AgentCore orchestrator. Everything comes from environment variables so the
same container image works in every account; CDK sets them (see infra/stacks/platform_stack.py)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    region: str = field(default_factory=lambda: os.environ.get("AWS_REGION", "us-east-1"))
    account_id: str = field(default_factory=lambda: os.environ.get("AWS_ACCOUNT_ID", "061039769766"))
    report_state_machine_arn: str = field(default_factory=lambda: os.environ.get(
        "REPORT_STATE_MACHINE_ARN", "arn:aws:states:us-east-1:061039769766:stateMachine:ESGReportGenerationStateMachine"))
    ghg_state_machine_arn: str = field(default_factory=lambda: os.environ.get("GHG_STATE_MACHINE_ARN", ""))
    sync_state_machine_arn: str = field(default_factory=lambda: os.environ.get("SYNC_STATE_MACHINE_ARN", ""))
    data_tools_function: str = field(default_factory=lambda: os.environ.get("DATA_TOOLS_FUNCTION", "esg-data-tools"))
    section_gen_function: str = field(default_factory=lambda: os.environ.get("SECTION_GEN_FUNCTION", "esg-section-gen"))
    validation_function: str = field(default_factory=lambda: os.environ.get("VALIDATION_FUNCTION", "esg-validation"))
    assembly_function: str = field(default_factory=lambda: os.environ.get("ASSEMBLY_FUNCTION", "esg-assembly-doc"))
    platform_function: str = field(default_factory=lambda: os.environ.get("PLATFORM_FUNCTION", "esg-platform-api"))
    output_bucket: str = field(default_factory=lambda: os.environ.get("OUTPUT_BUCKET", "esg-output-reports-061039769766"))
    kb_id: str = field(default_factory=lambda: os.environ.get("KB_ID", "WVREXI1LEI"))
    bank_id: str = field(default_factory=lambda: os.environ.get("BANK_ID", "GENERIC_FI_001"))
    # hard ceiling per section; the real stop is the money budget below or running out of untried strategies
    max_correction_attempts: int = field(default_factory=lambda: _int("MAX_CORRECTION_ATTEMPTS", 4))
    section_budget_usd: float = field(default_factory=lambda: _float("SECTION_BUDGET_USD", 0.40))
    run_budget_usd: float = field(default_factory=lambda: _float("RUN_BUDGET_USD", 1.50))
    agent_memory_table: str = field(default_factory=lambda: os.environ.get("AGENT_MEMORY_TABLE", ""))
    max_restarts: int = field(default_factory=lambda: _int("MAX_PIPELINE_RESTARTS", 1))
    poll_seconds: int = field(default_factory=lambda: _int("POLL_SECONDS", 20))
    max_wait_seconds: int = field(default_factory=lambda: _int("MAX_WAIT_SECONDS", 3300))
    lock_ttl_seconds: int = field(default_factory=lambda: _int("LOCK_TTL_SECONDS", 1800))
    available_years: tuple[int, ...] = (2023, 2024)


def load() -> Settings:
    return Settings()
