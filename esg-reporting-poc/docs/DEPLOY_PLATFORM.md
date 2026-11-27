# Deployment runbook (Windows, PowerShell)

Deploys the complete ESG Intelligence platform into an **empty** AWS account: backend with AWS CDK, frontend on
AWS Amplify Hosting from GitHub. Sections 1 to 9 were run on Windows with PowerShell on 27 November 2026; the first data
load (section 10) was in progress when this was written.

| | |
|---|---|
| Account / region | `061039769766` / `us-east-1` (one environment: production) |
| Git branch | `main-agentcore` (Amplify builds this branch on every push) |
| Time | about 1.5 hours for a first deployment, mostly waiting (RDS, Knowledge Base ingestion, first data sync) |
| Docker | not needed |

Run each step in order. Every block says **where** to run it. Paths are relative to the repository root `esg-chat-app\`.

---

## Contents
1. [Prerequisites (once per machine and account)](#1-prerequisites-once-per-machine-and-account)
2. [Get the code and set variables](#2-get-the-code-and-set-variables)
3. [Build the artifacts](#3-build-the-artifacts)
4. [Foundation stack, tables and Knowledge Base](#4-foundation-stack-tables-and-knowledge-base)
5. [Network and database stacks](#5-network-and-database-stacks)
6. [Data stack and source data](#6-data-stack-and-source-data)
7. [Platform stack (API, login, agent)](#7-platform-stack-api-login-agent)
8. [Users](#8-users)
9. [Frontend release on Amplify](#9-frontend-release-on-amplify)
10. [First data load and smoke test](#10-first-data-load-and-smoke-test)
11. [Day-2 operations](#11-day-2-operations)
12. [Troubleshooting](#12-troubleshooting)
13. [Teardown](#13-teardown)

Stack order (each stack depends on the one before):

```
EsgFoundationStack -> EsgNetworkStack -> EsgDatabaseStack -> EsgDataStack -> EsgPlatformStack
```

---

## 1. Prerequisites (once per machine and account)

### 1.1 Tools
Open **PowerShell** (normal user):
```powershell
winget install -e --id Amazon.AWSCLI
winget install -e --id Python.Python.3.12
winget install -e --id OpenJS.NodeJS.LTS
winget install -e --id Git.Git
```
Close and reopen PowerShell, then:
```powershell
npm install -g aws-cdk
python --version        # 3.12.x
cdk --version           # 2.x
```

### 1.2 Short paths (important on OneDrive)
Some files in the agent package have long paths. Windows limits paths to 260 characters. Either clone into a short
folder such as `C:\dev\` (recommended: it also keeps OneDrive from syncing the large `build\` folder), or enable long
paths once in an **Administrator** PowerShell and reopen PowerShell:
```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force
```

### 1.3 AWS credentials
```powershell
aws configure sso          # or: aws configure   (region us-east-1)
aws sts get-caller-identity
```
`Account` must be `061039769766`. An administrator role is required for the first deployment (it creates IAM roles).

### 1.4 Bedrock model access (AWS console)
Bedrock console, region **us-east-1**, *Model access*: enable
- **Anthropic Claude Sonnet 4.5**
- **Anthropic Claude Haiku 4.5**
- **Amazon Titan Text Embeddings V2** (without it the Knowledge Base ingestion fails)

### 1.5 Amplify app (AWS console, once)
1. Amplify console > *Create new app* > **GitHub** > authorise the Amplify GitHub App for the repository `esg-chat-app`.
2. Branch `main-agentcore`. Keep the detected build settings (they come from `amplify.yml` at the repository root). Save and deploy.
   The first build runs in demo mode (no backend yet); that is expected.
3. Note the **App ID** (for example `d2uq0q63fonlj3`). The app URL is `https://main-agentcore.<AppID>.amplifyapp.com`.

---

## 2. Get the code and set variables

```powershell
cd C:\dev                                   # any short folder
git clone https://github.com/radityar21/esg-chat-app.git
cd esg-chat-app
git checkout main-agentcore
cd esg-reporting-poc
```

Set these in **every new PowerShell window** (values for this account):
```powershell
$ACCT  = "061039769766"
$env:AWS_REGION = "us-east-1"
$APPID = "d2uq0q63fonlj3"
$APP   = "https://main-agentcore.$APPID.amplifyapp.com"
$SYNC  = "arn:aws:states:us-east-1:${ACCT}:stateMachine:ESGDataSyncStateMachine"
```

Create one Python environment for CDK and the helper scripts (from `esg-reporting-poc\`):
```powershell
python -m venv infra\.venv
.\infra\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r infra\requirements.txt boto3 pypdf
```
Reactivate with `.\infra\.venv\Scripts\Activate.ps1` in every new window. The prompt shows `(.venv)`.

Bootstrap CDK once per account and region:
```powershell
cdk bootstrap aws://$ACCT/us-east-1
```

---

## 3. Build the artifacts

From `esg-reporting-poc\`, venv active:
```powershell
python scripts\build_all.py
```
Expected last lines:
```
...build\agent.zip: 41.x MB zipped, 9x.x MB unzipped
all artifacts ready
```
It creates `build\` with: the six report Lambda packages, the python-docx layer (Linux x86_64), the boto3 and pg8000
layers, the Glue contract library and `agent.zip` (AgentCore runtime, Linux arm64). The `[notice] A new release of pip`
lines are harmless.

Re-run this after changing any Lambda, Glue contract or agent code, then deploy the stack that owns the code (section 11.1).

---

## 4. Foundation stack, tables and Knowledge Base

### 4.1 Deploy (about 2 minutes)
```powershell
cd infra
cdk deploy EsgFoundationStack --app "python app.py"
cd ..
```
Answer `y` to the IAM change prompt. Creates the six S3 buckets, the Athena workgroup, the four Glue ETL jobs, the six
report Lambdas, the report state machine, two SNS topics, the PII secret and the Knowledge Base (S3 Vectors).

### 4.2 Databases and tables
```powershell
python scripts\apply_ddl.py
```
Expected: 13 `ok` lines and `13 statements applied` (3 Glue databases, 10 Athena tables).

### 4.3 Knowledge Base documents (10 to 20 minutes)
```powershell
$f  = aws cloudformation describe-stacks --stack-name EsgFoundationStack --query "Stacks[0].Outputs" | ConvertFrom-Json
$KB = ($f | ? OutputKey -eq KnowledgeBaseId).OutputValue
$DS = ($f | ? OutputKey -eq KnowledgeBaseDataSourceId).OutputValue
python scripts\upload_kb_documents.py --kb-id $KB --data-source-id $DS
```
Uploads the 14 reference documents from `ESG Document\` (one PDF is split in two because semantic chunking accepts at
most 1,000,000 characters per file), 27 prompt and template files, then waits for ingestion.
Expected end: status `COMPLETE` with `numberOfDocumentsFailed: 0`. Safe to re-run: unchanged files are skipped.

---

## 5. Network and database stacks

About 10 minutes (RDS):
```powershell
cd infra
cdk deploy EsgNetworkStack EsgDatabaseStack --app "python app.py"
cd ..
```
Creates a VPC with two isolated subnets (no NAT, no internet), an S3 gateway endpoint, a Secrets Manager interface
endpoint, and RDS PostgreSQL 16 (encrypted, TLS only, private, 7-day backups, deletion protection).

---

## 6. Data stack and source data

### 6.1 Seed files and stack (about 5 minutes)
```powershell
aws s3 cp data\seed\rds "s3://esg-data-raw-$ACCT/seed/rds/" --recursive
cd infra
cdk deploy EsgDataStack --app "python app.py"
cd ..
```
Expected: 9 `upload:` lines, then the stack outputs `SyncStateMachineArn`, `ExtractJobName`, `SeedFunctionName`, `DataToolsFunctionName`.

### 6.2 Create the schema and load the data
The seed Lambda runs inside the VPC.
```powershell
'{"action":"init"}' | Set-Content p.json -Encoding ascii
aws lambda invoke --function-name esg-rds-seed --payload fileb://p.json --cli-binary-format raw-in-base64-out out.json
Get-Content out.json
```
Expected: `{"schema": "esg", "tables": [...], "reader": "esg_reader"}`
```powershell
'{"action":"load","reload":true}' | Set-Content p.json -Encoding ascii
aws lambda invoke --function-name esg-rds-seed --payload fileb://p.json --cli-binary-format raw-in-base64-out out.json
Get-Content out.json
```
Expected: `energy_consumption 5280, loan_portfolio 4400, hr_metrics 2, scope3_operational_activity 16, entity 10,
facility 722, emission_factor 82, activity_data 59097, esg_metric 341`. The last five are the group data
(subsidiaries, facilities, activity data, emission factors, ESG metrics) generated by `scripts\generate_group_data.py`.

### 6.3 Test one extract
```powershell
'{"reporting_year":2024,"tables":["hr_metrics"]}' | Set-Content in.json -Encoding ascii
$ex = aws stepfunctions start-execution --state-machine-arn $SYNC --input file://in.json --query executionArn --output text
Start-Sleep 150
aws stepfunctions describe-execution --execution-arn $ex --query "{status:status,output:output}"
aws s3 cp "s3://esg-output-reports-$ACCT/etl-reports/latest/hr_metrics_2024.json" -
```
Expected: execution `SUCCEEDED` with `"status":"OK"` for the table, and a contract report with `"status": "OK"`,
`"rows": 1`, `"wrote_raw": true`. If the execution is still `RUNNING`, wait and run the `describe-execution` line again.
The execution is `SUCCEEDED` even when a table fails: per-table results are read and acted on by the agent.

---

## 7. Platform stack (API, login, agent)

About 7 minutes:
```powershell
cd infra
cdk deploy EsgPlatformStack --app "python app.py" -c appUrl=$APP
cd ..
```
`appUrl` must be the exact Amplify origin, with no trailing slash. Read the outputs:
```powershell
$o = aws cloudformation describe-stacks --stack-name EsgPlatformStack --query "Stacks[0].Outputs" | ConvertFrom-Json
$o | Format-Table OutputKey, OutputValue -AutoSize
$API    = ($o | ? OutputKey -eq PlatformApiUrl).OutputValue
$POOL   = ($o | ? OutputKey -eq CognitoUserPoolId).OutputValue
$CLIENT = ($o | ? OutputKey -eq CognitoClientId).OutputValue
$DOMAIN = ($o | ? OutputKey -eq CognitoDomain).OutputValue
$RT     = ($o | ? OutputKey -eq AgentRuntimeArn).OutputValue
```

Verify:
```powershell
aws bedrock-agentcore-control get-agent-runtime --agent-runtime-id $RT.Split('/')[-1] --query "{status:status,reason:failureReason}"
Invoke-RestMethod "$API/health"                                                        # ok = True
try { Invoke-RestMethod "$API/portfolio" } catch { $_.Exception.Response.StatusCode }   # Unauthorized

'{"mode":"chat","prompt":"What can you do? Answer in two sentences."}' | Set-Content q.json -Encoding ascii
aws bedrock-agentcore invoke-agent-runtime --agent-runtime-arn $RT --runtime-session-id "test-session-0000000000000000000000000001" --payload fileb://q.json --content-type application/json --accept application/json resp.json
Get-Content resp.json
```
Expected: runtime `READY`, health `ok`, `Unauthorized` without a token, and a JSON answer from the agent.

---

## 8. Users

Nobody can self-register. Create each user and put them in a group: `admin` (everything, including scans and
attestations) or `viewer` (read, chat, scenarios). A user without a group can sign in but every API call returns 403.
```powershell
$email = "name@company.com"
aws cognito-idp admin-create-user --user-pool-id $POOL --username $email --user-attributes Name=email,Value=$email Name=email_verified,Value=true --desired-delivery-mediums EMAIL
aws cognito-idp admin-add-user-to-group --user-pool-id $POOL --username $email --group-name admin
```
The user receives a temporary password by email (sender `no-reply@verificationemail.com`, check spam) and must change
it at the first sign-in. Password rules: 12+ characters with upper and lower case, a digit and a symbol.
Set a password directly instead: `aws cognito-idp admin-set-user-password --user-pool-id $POOL --username $email --password "<password>" --permanent`.

---

## 9. Frontend release on Amplify

```powershell
aws amplify update-app --app-id $APPID --environment-variables "VITE_PLATFORM_API_URL=$API,VITE_COGNITO_DOMAIN=$DOMAIN,VITE_COGNITO_CLIENT_ID=$CLIENT"
aws amplify start-job --app-id $APPID --branch-name main-agentcore --job-type RELEASE
aws amplify list-jobs --app-id $APPID --branch-name main-agentcore --max-results 1 --query "jobSummaries[0].status"
```
`update-app --environment-variables` replaces the whole list. Wait for `SUCCEED` (about 3 minutes).
Without these three variables the frontend runs in demo mode (badge "Demo data", no sign-in).

---

## 10. First data load and smoke test

Open the Amplify URL, sign in, open **AI Assistant** and ask, one after the other:

| # | Ask the assistant | What happens | Time |
|---|---|---|---|
| 1 | `Sync the 2024 data from the database` | Extracts the 9 tables from RDS with contract checks, then runs the Scope 1/2/3 ETL and aggregation | 10-15 min |
| 2 | `Sync the 2023 data from the database` | Same for the base year | 10-15 min |
| 3 | `Generate a GRI 305 report for 2024` | Report pipeline plus adaptive self-correction; DOCX in Report Runs | 10-20 min |

Progress is visible in the **Agent activity** panel. Until steps 1 and 2 finish, the GHG, Portfolio and Command Center
pages show "—" or a data error (the aggregated tables are empty).

Checklist:
- [ ] Sign-in works, the sidebar shows your email and role
- [ ] Command Center, Compliance, Portfolio, GHG Inventory show the **Live · AWS** badge
- [ ] Reports & Scenarios: scenario tab shows live numbers; moving a slider changes them
- [ ] AI Governance: PII masking works; FinOps shows usage after the first report
- [ ] Report Runs lists the report with a DOCX link; Reference lists the KB documents
- [ ] ESG Data Hub, GHG Accounting and ESG Metrics show **Live · AWS** and about 25 data alerts per year (planted gaps)

---

## 11. Day-2 operations

### 11.1 Deploying code changes
Push to `main-agentcore` redeploys the frontend automatically. For backend code: `python scripts\build_all.py`, then
deploy the owning stack:

| Changed | Deploy |
|---|---|
| `lambda\validate_input`, `athena_query`, `section_gen`, `validation`, `filter_sections`, `assembly_doc`, `glue_jobs\glue_job_*.py`, `step_functions\esg_orchestrator.asl.json` | `EsgFoundationStack` |
| `glue_jobs\esg_extract_rds.py`, `glue_jobs\esg_contracts.py`, `lambda\rds_seed`, `lambda\data_tools`, `step_functions\esg_data_sync.asl.json` | `EsgDataStack` |
| `agentcore\`, `lambda\platform_api`, `lambda\agent_trigger`, `step_functions\esg_ghg_inventory.asl.json` | `EsgPlatformStack` |
| `lambda\_shared` (shared modules) | all three: `EsgFoundationStack`, `EsgDataStack`, `EsgPlatformStack` |
| `prompts\`, `templates\` | `python scripts\upload_kb_documents.py --skip-ingest` |
| Documents in `ESG Document\` | `python scripts\upload_kb_documents.py --kb-id $KB --data-source-id $DS` |
| `sql\ddl\` | `python scripts\apply_ddl.py` (CREATE IF NOT EXISTS only; altering a table needs a manual DROP first) |

Always pass `-c appUrl=$APP` when deploying `EsgPlatformStack`. Changing `agentcore\requirements.txt` requires
regenerating `agentcore\requirements.lock.txt` on Linux (instructions in the file).

### 11.2 Upgrading an existing deployment to the Data Hub release (one time)
For an account that already runs the platform (the release with the Report Builder, chat history and the ESG Data Hub).
The frontend is released by Amplify on the push; until the steps below are done the new pages show
"Demo data · live data failed".
```powershell
git pull
python scripts\build_all.py
cd infra
cdk deploy EsgFoundationStack EsgDataStack EsgPlatformStack --app "python app.py" -c appUrl=$APP --require-approval never
cd ..
python scripts\apply_ddl.py                                                  # 19 statements: 5 new tables + the ledger view
aws s3 cp data\seed\rds "s3://esg-data-raw-$ACCT/seed/rds/" --recursive      # 5 new seed files
'{"action":"init"}' | Set-Content p.json -Encoding ascii
aws lambda invoke --function-name esg-rds-seed --payload fileb://p.json --cli-binary-format raw-in-base64-out out.json; Get-Content out.json
'{"action":"load","reload":true}' | Set-Content p.json -Encoding ascii
aws lambda invoke --function-name esg-rds-seed --payload fileb://p.json --cli-binary-format raw-in-base64-out out.json; Get-Content out.json
```
Then, in the AI Assistant: `Sync the 2023 data from the database` and, when it finished, `Sync the 2024 data from the
database` (about 10 minutes each). Open **ESG Data Hub** and press **Refresh**.

What the deploy changes: `EsgFoundationStack` (section generator template map and report catalog, report state machine
passes the language and sections), `EsgDataStack` (contracts and seed for the 5 new tables, data sync runs 4 tables in
parallel), `EsgPlatformStack` (Report Builder, findings workflow, conversations table, AgentCore Memory, `/data/*`
routes, agent tool `get_esg_data`).

Regenerating the synthetic data (optional): `python scripts\generate_group_data.py` (fixed seed, same files), then
`pip install duckdb` and `python scripts\datahub_local.py` to refresh the frontend demo snapshot.

### 11.3 Demonstrating data triage
```powershell
'{"action":"inject","kind":"rename_column"}' | Set-Content p.json -Encoding ascii     # blocking: hr_metrics contract fails
aws lambda invoke --function-name esg-rds-seed --payload fileb://p.json --cli-binary-format raw-in-base64-out out.json
```
Ask the assistant to sync 2024: the agent rejects `hr_metrics`, explains the column problem, keeps the last good data and
does not start the ETL. `"kind":"range"` plants a warning instead (data loads, a review note asks to confirm). Restore:
```powershell
'{"action":"reset"}' | Set-Content p.json -Encoding ascii
aws lambda invoke --function-name esg-rds-seed --payload fileb://p.json --cli-binary-format raw-in-base64-out out.json
```

### 11.4 Logs
```powershell
aws logs tail /aws/bedrock-agentcore/runtimes/$($RT.Split('/')[-1])-DEFAULT --since 30m      # agent
aws logs tail /aws/lambda/esg-platform-api --since 30m                                       # API
aws logs tail /aws/lambda/esg-section-gen --since 30m                                        # report sections
aws logs tail /aws-glue/jobs/error --since 30m                                               # Glue errors
```

### 11.5 Tuning without code changes
Runtime environment variables (AgentCore console > runtime > edit, or change `platform_stack.py` and redeploy):
`MODEL_ROUTING_PROFILE` (`quality` | `balanced` | `economy`), `SECTION_BUDGET_USD` (0.40), `RUN_BUDGET_USD` (1.50),
`MAX_CORRECTION_ATTEMPTS` (4). Validator: `VALIDATOR_CALIBRATION` on `esg-validation` (`on` | `off`).

### 11.6 Retention and running cost
- Logs 14 days. DynamoDB usage and chat-job tables 14 days (TTL). S3 prefixes `agent-ledger/`, `executions/`,
  `platform-cache/`, `etl-reports/` and Athena results 14 days.
- Kept: generated reports, raw/curated/aggregated data, KB documents, compliance attestations, strategy memory.
- Always-on cost (estimate, verify with the AWS Pricing Calculator): RDS db.t4g.small with 50 GB (about USD 27/month),
  Secrets Manager interface endpoint in two AZs (about USD 15/month), 4 secrets (about USD 1.60/month).
  Everything else is pay per use (Bedrock tokens, Glue DPU-minutes, Lambda, S3 Vectors, Athena scans).

---

## 12. Troubleshooting

Errors met during the first deployment and what they mean:

| Symptom | Cause | Fix |
|---|---|---|
| `cdk` cannot import `aws_cdk` | venv not active | `.\infra\.venv\Scripts\Activate.ps1` from `esg-reporting-poc\` |
| `build/... is missing. Run: python scripts/build_all.py` | artifacts not built, or built from another folder | run step 3 from `esg-reporting-poc\` |
| `can't open file ...\infra\scripts\...` | running a script from `infra\` | `cd ..` to `esg-reporting-poc\` |
| `NoSuchBucket` on upload | the foundation stack is not deployed | deploy step 4 first |
| pip `ResolutionImpossible` building the agent zip | (fixed) the build now installs a Linux-resolved lock file with `--no-deps` | `git pull`, rerun step 3 |
| Path too long / file not found during the build | Windows 260-character path limit | section 1.2 |
| KB ingestion: `File body text exceeds size limit of 1000000 for semantic chunking` | (fixed) large PDFs are now split | rerun 4.3 |
| Extract: `No module named 'esg_contracts'` / `relation "(SELECT ...)" does not exist` | (fixed) Glue packaging and table read | `git pull`, `build_all`, redeploy `EsgDataStack` |
| Contract report `0 rows found` | the seed `load` action was not run | step 6.2 |
| Platform deploy: `LogGroup ... already exists` / `OpenTelemetry instrumentation executable not found` | (fixed) log retention and portable console scripts | `git pull`, `build_all`, redeploy |
| A first-time stack creation failed and rolled back | stack is in `ROLLBACK_COMPLETE` | `aws cloudformation delete-stack --stack-name <name>`, wait, deploy again |
| Sign-in loops or `redirect_mismatch` | `appUrl` differs from the Amplify URL | redeploy `EsgPlatformStack` with the exact `-c appUrl=` |
| API returns 403 after sign-in | user is in no group | `admin-add-user-to-group` (section 8) |
| Pages show "Demo data" after release | Amplify variables missing or misspelled | `aws amplify get-app --app-id $APPID --query "app.environmentVariables"` |
| Badge "Demo data · live data failed: data query failed" | an Athena query failed (permissions, missing table or data) | `aws logs tail /aws/lambda/esg-platform-api --since 30m` |
| Compliance items "Not checked" | the readiness probe could not query Athena | same log; once fixed the items are scored again |

When a deploy fails, the useful part is the `Failed resources` block and the CloudTrail lines under it.

---

## 13. Teardown

Delete in reverse order:
```powershell
cd infra
cdk destroy EsgPlatformStack EsgDataStack --app "python app.py" -c appUrl=$APP
aws rds modify-db-instance --db-instance-identifier esg-source-db --no-deletion-protection --apply-immediately
cdk destroy EsgDatabaseStack EsgNetworkStack EsgFoundationStack --app "python app.py" -c appUrl=$APP
cd ..
```
Retained on purpose (delete manually if you really want everything gone): the six S3 buckets, the RDS final snapshot, the Cognito user pool, the strategy-memory table and the secrets (Secrets Manager keeps them
for a recovery window). If the S3 Vectors bucket or index refuses to delete, empty it in the S3 console and run the
destroy again. The Amplify app is managed in the Amplify console.
