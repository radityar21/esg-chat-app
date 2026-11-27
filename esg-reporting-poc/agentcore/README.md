# ESG Orchestrator: AgentCore Runtime (outer) + Step Functions (inner)

```
User / UI ──► platform API ──► AgentCore Runtime (this package)
                                   │  plan_pipeline → start_pipeline → get_run_status → explain_run
                                   │
                                   ├─► sfn:StartExecution ──► Step Functions (inner engine)
                                   │        Glue ETL ─► Athena ─► Map: SectionGen → Validation(21 rules) ─► Assembly
                                   │
                                   └─► self-correction loop (deterministic, tested)
                                            for each section that failed validation:
                                              classify rule → fixable text problem?  yes → regenerate with a corrective prompt
                                                                                     no  → escalate (source-data issue)
                                              re-validate → repeat (max 2) → re-assemble the DOCX
```

| File | Role |
|------|------|
| `app.py` | AgentCore entrypoint (`chat`, `supervise`, `status`, `ledger` modes), HealthyBusy ping |
| `orchestrator/agent.py` | Strands agent, system prompt and tool wrappers |
| `orchestrator/service.py` | All actions as plain Python (what the tools call). Never raises into the LLM |
| `orchestrator/healer.py` | `SelfHealingSupervisor`: start, wait, diagnose, repair, re-assemble |
| `orchestrator/rules.py` | Validation rule catalogue: fixable-by-regeneration vs source-data issue |
| `orchestrator/diagnose.py` | Turns Step Functions history into category, cause, retryable, advice |
| `orchestrator/pipelines.py` | Pipeline registry, request planner, Step Functions input builder |
| `orchestrator/ledger.py` | S3 ledger (agent timeline) and atomic claim so a run is never supervised twice |

## Why the loop is deterministic Python and not an LLM loop
Regenerating a section is a mechanical, rule-driven action (the 21 rules say exactly what is wrong). Keeping it in
code makes it reproducible, cheap, bounded (2 attempts per section, 1 pipeline restart) and unit-tested. The LLM does
what it is good at: understanding the request, choosing the pipeline, and explaining outcomes.

## Two ways supervision starts
1. **Chat**: `start_pipeline` launches the run and a background supervisor in the same runtime session.
2. **Event-driven**: an EventBridge rule fires when any report/GHG execution reaches a terminal state and the
   `esg-agent-trigger` Lambda calls this runtime with `mode=supervise`. This covers runs started from the console or
   by the old Bedrock Agent. The ledger lock makes the two paths safe together.

## Run the tests (no AWS, no LLM)
```bash
cd esg-reporting-poc
python -m venv .venv && . .venv/bin/activate
pip install pytest boto3 strands-agents bedrock-agentcore
python -m pytest tests/agentcore -q
```

## Local smoke run of the runtime
```bash
cd esg-reporting-poc/agentcore
pip install -r requirements.txt
python app.py                       # listens on :8080
curl -s localhost:8080/invocations -H 'content-type: application/json' \
  -d '{"mode":"chat","prompt":"Halo, apa saja yang bisa kamu lakukan?"}'
```
Deployment is done by the CDK stack in `infra/` (see `docs/DEPLOY_PLATFORM.md`).
