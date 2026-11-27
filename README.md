# ESG Intelligence Platform

AI platform for a bank's sustainability work: compliance readiness for PSPK, multi-framework report generation
(GRI 305, IFRS S2, CSRD ESRS E1, OJK PSPK), climate scenarios, PCAF portfolio analytics, a GHG Protocol inventory, and
AI governance (PII masking, model routing, token cost tracking). An Amazon Bedrock **AgentCore** agent is the outer
orchestrator: it decides what to run, supervises the AWS Step Functions pipelines, repairs report sections that fail
validation, and explains the outcome.

The data is synthetic and belongs to a fictional bank, **Bank Nusantara Sejahtera**. It is treated as real data.

| What you want | Where to go |
|---|---|
| Deploy it (Windows, from an empty account) | [`esg-reporting-poc/docs/DEPLOY_PLATFORM.md`](esg-reporting-poc/docs/DEPLOY_PLATFORM.md) |
| Understand how it works (flows, architecture, design decisions) | [`esg-reporting-poc/docs/ARCHITECTURE.md`](esg-reporting-poc/docs/ARCHITECTURE.md) |
| Details of the agent and the self-correction loop | [`esg-reporting-poc/docs/AGENTCORE_ORCHESTRATION.md`](esg-reporting-poc/docs/AGENTCORE_ORCHESTRATION.md) |
| Frontend details | [`esg-chat-app-react/README.md`](esg-chat-app-react/README.md) |

Live app: `https://main-agentcore.d2uq0q63fonlj3.amplifyapp.com` (sign-in required). Branch `main-agentcore` is
production: every push to it rebuilds the frontend. **Do not use or change `main-workflow`.**

---

## How to read this repository

Two folders matter for the running system. Everything else is reference material or history.

```
esg-chat-app/                        repository root
├── esg-chat-app-react/              FRONTEND  (React + Vite + Tailwind, deployed by Amplify)
├── esg-reporting-poc/               BACKEND   (agent, Lambdas, Glue, Step Functions, CDK)
├── amplify.yml                      Amplify build settings for the frontend
├── .github/workflows/ci.yml         CI: backend tests, artifact build, CDK synth, frontend build
│
├── ESG Document/                    source documents for the Knowledge Base (standards, sample reports)
├── architecture/                    older draw.io diagrams (pre-AgentCore)
├── reference docs/                  original requirement spec, architecture write-ups, pricing estimate
├── prompts/                         the original spec outline used to start the project
├── esg-chat-app/                    LEGACY chat prototype (single HTML page + Bedrock Agent proxy)
└── DEPLOYMENT_GUIDE.md, DEPLOYMENT_SUMMARY.md, INFRASTRUCTURE_SPEC.md
                                     LEGACY docs of the first version (manual deployment, ap-southeast-1 plan,
                                     OpenSearch KB). Kept for history; the current guide is DEPLOY_PLATFORM.md.
```

### Backend: `esg-reporting-poc/`

```
esg-reporting-poc/
├── agentcore/                AgentCore Runtime agent (the outer orchestrator)
│   ├── app.py                runtime entry point: modes chat | supervise | status | ledger
│   ├── orchestrator/
│   │   ├── agent.py          Strands agent: system prompt and its 15 tools
│   │   ├── service.py        what the tools call (start, status, explain, platform, data tools)
│   │   ├── pipelines.py      pipeline registry and the deterministic request planner
│   │   ├── healer.py         supervisor: watches Step Functions, repairs failed report sections
│   │   ├── strategies.py     adaptive correction policy (strategy choice, model routing, budgets, memory)
│   │   ├── rules.py          the validation rules and what to do when each one fails
│   │   ├── datasync.py       triage of data syncs from the source database
│   │   ├── diagnose.py       explains failed Step Functions executions
│   │   ├── ledger.py         per-run timeline stored in S3 (shown in the UI)
│   │   ├── aws.py            the only place that talks to AWS (so tests can fake it)
│   │   └── config.py         settings from environment variables
│   ├── requirements.txt      direct dependencies   |  requirements.lock.txt  fully resolved set used by the build
│   └── Dockerfile            optional container packaging (default is a zip, no Docker)
│
├── lambda/                   AWS Lambda functions
│   ├── validate_input/  athena_query/  section_gen/  validation/  filter_sections/  assembly_doc/
│   │                         the report pipeline, in execution order (validation = the 21 rules)
│   ├── platform_api/         HTTP API behind Cognito: compliance, GHG, portfolio, scenarios, governance,
│   │                         agent chat, report history, reference documents
│   ├── agent_trigger/        EventBridge: report pipeline finished -> agent supervises it
│   ├── rds_seed/             creates the source database schema and loads the synthetic data
│   ├── data_tools/           read-only database tools for the agent
│   ├── _shared/              modules used by several functions and the agent (model routing, PII guard,
│   │                         usage metering, scenario engine, domain constants, RDS connection)
│   └── dashboard_data/  history/  review_handler/  status_check/
│                             LEGACY functions of the first version (not deployed by CDK)
│
├── glue_jobs/                AWS Glue (PySpark)
│   ├── glue_job_scope1_ghg.py, glue_job_scope2_electricity.py, glue_job_scope3_pcaf.py, glue_job_aggregation.py
│   │                         raw -> curated -> aggregated GHG calculations
│   ├── esg_extract_rds.py    source database -> raw zone, with data-contract checks
│   └── esg_contracts.py      the data contracts (columns, types, ranges, keys) and the checker
│
├── step_functions/           state machine definitions (ASL)
│   ├── esg_orchestrator.asl.json     report generation (deployed)
│   ├── esg_ghg_inventory.asl.json    ETL + GHG inventory (deployed)
│   ├── esg_data_sync.asl.json        extract from the source database (deployed)
│   └── other *.asl.json              older variants and backups
│
├── infra/                    AWS CDK (Python). app.py wires the five stacks:
│   └── stacks/               foundation_stack.py, network_stack.py, database_stack.py, data_stack.py, platform_stack.py
│                             (esg_infra_stack.py is an empty placeholder from the first version)
│
├── prompts/                  base prompt + one overlay per framework (uploaded to the KB bucket)
├── templates/                one prompt template per report section (uploaded to the KB bucket)
├── sql/ddl/                  Glue databases and Athena tables (applied by scripts/apply_ddl.py)
├── data/
│   ├── seed/rds/             the synthetic source data loaded into PostgreSQL (CSV.gz)
│   ├── synthetic/            the same data as Parquet, by table and year
│   └── kb_metadata/          metadata files generated for the KB documents
├── scripts/                  build_all.py (artifacts), apply_ddl.py, upload_kb_documents.py, build_agent_zip.py,
│                             generate_*.py (synthetic data). setup_account.sh, deploy_lambdas.sh, build_layer.sh,
│                             upload_to_s3.bat and the *.md notes are LEGACY from the first version
├── tests/                    pytest suite (agent, platform API, contracts, data tools, validation, DDL)
├── docs/                     DEPLOY_PLATFORM.md, ARCHITECTURE.md, AGENTCORE_ORCHESTRATION.md, and older notes
├── benchmark_advisory/       benchmark and recommendation texts with KB metadata
├── config/esg_config.yaml    configuration of the first version (reference)
├── agent/                    LEGACY Bedrock Agent (action group, OpenAPI schema) replaced by agentcore/
└── result/                   sample outputs (DOCX, PPTX) of earlier runs
```

### Frontend: `esg-chat-app-react/`

```
esg-chat-app-react/src/
├── App.jsx                   page switcher, sign-in gate, keys 1-9 jump between pages (presenter mode)
├── pages/                    Home (Command Center), Compliance, Frameworks (Reports & Scenarios), Portfolio,
│                             Governance, GhgInventory, DataHub (ESG Data Hub), GhgAccounting, EsgMetrics,
│                             Chat (AI Assistant), ReportBuilder, Reports (Report Runs), Reference
│                             Overview.jsx and Analytics.jsx are older pages, not in the menu
├── components/               ui.jsx (design system), Sidebar, AgentActivity (runs, timeline, review notes), RunProgress (checkpoints),
│                             AuthGate (sign-in screen), SourceBadge ("Live · AWS" vs "Demo data"), FacilityDrawer (audit trail)
├── lib/                      platform.js (API client, live/demo switch, async chat), auth.js (Cognito PKCE),
│                             datahub.js (Data Hub client with the demo snapshot fallback)
├── data/                     demo datasets and adapters that turn API responses into page data;
│                             datahub_demo.json is generated by esg-reporting-poc/scripts/datahub_local.py
└── api.js                    LEGACY client of the first version's REST API (used only in demo mode)
```
Live or demo: with the three `VITE_*` variables set (Amplify environment) every page reads the platform API and shows
**Live · AWS**; without them the pages use the bundled demo data and show **Demo data**.

---

## Where to find things

| I want to... | Look in |
|---|---|
| Change what the agent says or which tools it has | `agentcore/orchestrator/agent.py` |
| Change how failed sections are repaired | `agentcore/orchestrator/strategies.py`, `healer.py`, `rules.py` |
| Change routing of requests to pipelines | `agentcore/orchestrator/pipelines.py` |
| Change a validation rule | `lambda/validation/handler.py`, then `agentcore/orchestrator/rules.py` (fix instruction) |
| Change the wording of a report section | `templates/section_*.txt`, `prompts/*.txt` |
| Change a GHG calculation or emission factor | `glue_jobs/glue_job_scope*.py`, `glue_job_aggregation.py` |
| Change a data contract | `glue_jobs/esg_contracts.py` |
| Change the group synthetic data (entities, facilities, activity, metrics) | `scripts/generate_group_data.py`, then `scripts/datahub_local.py` for the demo snapshot |
| Change an emission factor of the group ledger | `emission_factor` seed (generator `COMMON_FACTORS`, `GRID_*`), ledger view in `sql/ddl/06_group_data.sql` |
| Change which ESG metrics are expected, or a data alert rule | `lambda/_shared/esg_metric_catalog.py`, `lambda/platform_api/datahub.py` (`data_alerts`) |
| Change report sections per framework | `lambda/_shared/report_catalog.py` |
| Change the Report Builder, template versions or saved configurations | `lambda/platform_api/report_builder.py`, `esg-chat-app-react/src/pages/ReportBuilder.jsx` |
| Change chat history | `lambda/platform_api/conversations.py` (UI list), `agentcore/app.py` (AgentCore Memory) |
| Change the DOCX layout | `lambda/assembly_doc/handler.py` |
| Change the PSPK checklist or regulatory sources | `lambda/platform_api/config/pspk_checklist.json` |
| Change peers or scenario assumptions | `lambda/platform_api/config/peers.json`, `lambda/_shared/scenario_engine.py`, `esg_domain.py` |
| Change model prices or routing profiles | `lambda/_shared/model_routing.py` |
| Change PII rules | `lambda/_shared/pii_guard.py` (and the guardrail in `infra/stacks/platform_stack.py`) |
| Add an API endpoint | `lambda/platform_api/handler.py` (routes) + a module in `lambda/platform_api/` |
| Add an AWS resource or permission | `infra/stacks/*.py` (see the stack table in ARCHITECTURE.md) |
| Change a page | `esg-chat-app-react/src/pages/` |
| Change colours, cards, charts style | `esg-chat-app-react/src/components/ui.jsx`, `tailwind.config.js` |
| Change the run checkpoints shown in the UI | `lambda/platform_api/progress.py`, `esg-chat-app-react/src/components/RunProgress.jsx` |
| See why a run failed | Report Runs page (checkpoints and agent timeline), or the logs in DEPLOY_PLATFORM.md section 11.4 |

---

## Run the tests

```powershell
cd esg-reporting-poc
python -m venv .venv-test; .\.venv-test\Scripts\Activate.ps1
pip install pytest boto3 pyyaml pg8000 aws-cdk-lib constructs
python -m pytest tests -q
```
The tests use in-memory fakes; they make no AWS calls. Frontend: `cd esg-chat-app-react; npm ci; npm run build`.

---

## Conventions

- **Branches.** `main-agentcore` = production (Amplify). Work on a feature branch and open a pull request into it.
  `main-workflow` is a separate line of work and must not be touched.
- **Infrastructure only through CDK.** Do not create or edit resources in the console (except Amplify app settings,
  Bedrock model access and Cognito users). Deploy order and commands: DEPLOY_PLATFORM.md.
- **No secrets in code.** Credentials live in Secrets Manager (`esg/pii-token-secret`, `esg/rds/master`, `esg/rds/reader`).
- **Numbers in reports come from data, never from the model.** The validator checks every figure against the source.
- **Peers, regulatory sources and the TKBI split per sector are illustrative** and labelled as such in the UI.

## Image credits
Photos from [Unsplash](https://unsplash.com) under the Unsplash License; details in
[`esg-chat-app-react/README.md`](esg-chat-app-react/README.md#image-credits). Credits are not shown in the UI on purpose.
