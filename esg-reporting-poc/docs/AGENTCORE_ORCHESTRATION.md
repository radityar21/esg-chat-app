# AgentCore orchestration and self-correction

AgentCore Runtime is the outer orchestrator. Step Functions stays the inner execution engine.

```
User / UI ──► platform API (Lambda) ──invoke_agent_runtime──► AgentCore Runtime (esg_orchestrator)
                                                               │  Strands agent: routes the request, explains results
                                                               │  ToolService: start / status / supervise / explain
                                                               ▼
                         sfn:StartExecution ──► Step Functions (report or GHG inventory state machine)
                                                 Glue ETL · parallel section generation · validation · assembly
                                                               │
EventBridge "Execution Status Change" ──► esg-agent-trigger ──► Runtime mode=supervise
                                                               ▼
                         Healer: read validation results ─► regenerate failed sections with a corrected prompt
                                 ─► re-validate ─► re-assemble ─► ledger in S3 (agent-ledger/<id>.json)
```

## What the agent decides
- Which pipeline to run (`esg_report` or `ghg_inventory`), for which year and framework.
- When a run ends, whether each section is fine, repairable, or a source-data problem.
- How to explain a failure in plain language (`explain_run`).

## Self-correction loop (`agentcore/orchestrator/healer.py` + `strategies.py`)
The loop is adaptive and the validator stays the only judge. The LLM routes requests, explains results and, as one
optional strategy, writes a short correction hint ("critic"). It never decides whether a section passed.

**1. Classify the failure** from the failed rules: `structural` (VAL-STR), `numeric` (VAL-NUM), `language` (VAL-PRH),
or `generate` (section missing). Source-data rules (VAL-NUM-02, VAL-NUM-06) are never regenerated: they are escalated with an ETL note.

**2. Pick the next strategy** among the untried ones for that failure type:

| Strategy | Model | What changes in the regeneration prompt |
|---|---|---|
| `fix_cheap` | Haiku | Corrective instructions for the failed rules |
| `fix_strong` | Sonnet | Same instructions, stronger model |
| `grounded_cheap` / `grounded_strong` | Haiku / Sonnet | Adds the list of numbers allowed (taken from the source metrics) |
| `critic_strong` | Haiku writes a hint, Sonnet regenerates | Adds an AI-written, sanitised hint (links and markup removed) |
| `minimal_safe` | Sonnet | Short text, figures only in tables. Always the last resort |

Order = expected success per dollar. The expected success starts from a prior and is updated by **memory**: every attempt
records success or failure per `failure type#strategy` in a DynamoDB table (stack output `AgentMemoryTableName`) (atomic counters).
A strategy that keeps failing for a failure type moves down; one that keeps working moves up. This is what makes the
multi-model routing adaptive: cheap models are tried first only while they work.

**3. Stop conditions** (whichever comes first): validation passes; only source-data problems remain; every applicable
strategy was tried; the section budget (`SECTION_BUDGET_USD`, 0.40) or the run budget (`RUN_BUDGET_USD`, 1.50) would be exceeded;
the hard ceiling `MAX_CORRECTION_ATTEMPTS` (4). A pipeline that failed for a transient reason is restarted once.

**4. Review notes.** Instead of blocking, an unresolved section stays in the report with warnings, and the run result carries
plain-language notes (`result.notes`: `info` repaired, `review` needs review before publishing, `action` fix the source data)
and the repair spend. The UI shows them under "Review notes" in the agent timeline. There is no approval gate yet.

Each step is an event in the ledger (`agent-ledger/<id>.json`). A lock object (`If-None-Match`) prevents two supervisors
from working on one run. Not included: retrieving extra knowledge-base context as a strategy.

## Data sync from the source database (`datasync.py`)
`data_sync` is a third pipeline: RDS PostgreSQL → Glue JDBC job `esg-extract-rds` (one run per table, two in parallel) →
S3 raw zone (same layout as the Athena tables) → the existing ETL. The Glue job checks a data contract
(`glue_jobs/esg_contracts.py`) BEFORE it writes: a blocking violation (missing column, wrong type, no rows, null or duplicate keys)
fails the job and the raw zone keeps the last good data; warnings (out-of-range values, unexpected categories) are loaded and reported.
The agent then decides:

| Situation | Decision |
|---|---|
| Table loaded, no warnings | Note "loaded N rows" |
| Table loaded with warnings | Keep the data, note asks the data owner to confirm |
| Failure looks temporary (timeout, connection, throttling) | Retry only that table, once |
| Contract violation | Escalate with the rule, the column and a concrete suggestion; never regenerate or overwrite |
| Access problem or unknown error | Escalate with the first lines of the cause |
| Every table loaded | Start the downstream ETL (GHG inventory pipeline) and wait for it |
| Any table not loaded | Do not start the ETL (no mixing fresh and stale tables) |

Read-only tools for the agent live in `esg-data-tools` (inside the VPC, SELECT-only database user): list tables with
row counts per year, preview up to 20 rows, read the latest contract report.

## Validator calibration (`VALIDATOR_CALIBRATION`, default `on`)
`docs/VALIDATION_FALSE_POSITIVES.md` documents that the numeric rules flagged correct numbers (derived percentages,
column totals, nested values). Looping on those false positives would burn tokens and degrade text. With calibration on:
`_build_allowed_values` walks nested data recursively and also allows derived percentages and column totals.
Set `VALIDATOR_CALIBRATION=off` on `esg-validation` to restore the previous behaviour.

## Limits
- Strategy memory lives in DynamoDB, not in AgentCore Memory. AgentCore Memory is a candidate for chat context later.
- The Step Functions `RetryGeneration` path is unchanged (a blind retry). The agent does the informed correction afterwards.
- The orchestrator calls Lambdas directly to regenerate a section, so a corrected report is assembled by `esg-assembly-doc` and stored next to the original.
- The Docker image build, `cdk deploy` and live AWS calls were not run in the development sandbox. Logic is covered by unit tests with fakes (`tests/agentcore`, `tests/platform_api`).
