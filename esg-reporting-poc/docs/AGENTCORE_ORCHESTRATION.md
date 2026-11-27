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

## Self-correction loop (`agentcore/orchestrator/healer.py`)
The loop is deterministic Python. The LLM routes and explains; it does not decide whether to retry.
Reasons: reproducible, bounded cost, unit-testable.

| Situation | Action |
|---|---|
| Section passes (`PASS`, `INCLUDED`) | Leave as is |
| Failed rules are `generation` rules (wording, unsupported numbers, structure) | Regenerate with a correction block listing the failed rules and the allowed values, then re-validate. Up to `MAX_CORRECTION_ATTEMPTS` (2) |
| Failed rules are source-data rules (VAL-NUM-02, VAL-NUM-06) | Do not regenerate. Escalate with an explanation of the data problem |
| Section missing or validation did not run | Generate or re-validate |
| Pipeline failed, cause looks transient | Restart once (`MAX_PIPELINE_RESTARTS`) |
| Pipeline failed, any other cause | Escalate with a diagnosis (failed state, error, hint) |

Each step is an event in the ledger; the UI shows it as the "Orchestrator timeline". A lock object
(`agent-ledger/<id>.lock`, created with `If-None-Match`) prevents two supervisors from working on one run.

## Validator calibration (`VALIDATOR_CALIBRATION`, default `on`)
`docs/VALIDATION_FALSE_POSITIVES.md` documents that the numeric rules flagged correct numbers (derived percentages,
column totals, nested values). Looping on those false positives would burn tokens and degrade text. With calibration on:
`_build_allowed_values` walks nested data recursively and also allows derived percentages and column totals.
Set `VALIDATOR_CALIBRATION=off` on `esg-validation` to restore the previous behaviour.

## Limits
- The Step Functions `RetryGeneration` path is unchanged (a blind retry). The agent does the informed correction afterwards.
- The orchestrator calls Lambdas directly to regenerate a section, so a corrected report is assembled by `esg-assembly-doc` and stored next to the original.
- The Docker image build, `cdk deploy` and live AWS calls were not run in the development sandbox. Logic is covered by unit tests with fakes (`tests/agentcore`, `tests/platform_api`).
