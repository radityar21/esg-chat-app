# Deploying the ESG Intelligence platform

Account `061039769766`, region `us-east-1`. Prerequisites: AWS CLI with admin-level credentials, Python 3.11+,
Node 18+, AWS CDK CLI v2, Docker with buildx (ARM64 image), Bedrock model access for Claude Sonnet 4.5 and Haiku 4.5,
CDK bootstrapped (`cdk bootstrap aws://061039769766/us-east-1`).

All commands run from `esg-reporting-poc/` unless stated.

## 1. Data: new Scope 3 table
```bash
aws s3 sync data/synthetic/scope3_operational s3://esg-data-raw-061039769766/raw/scope3_operational_activity/ --exclude "*.csv"
# run sql/ddl/05_scope3_operational.sql in Athena (workgroup esg-reporting-workgroup)
```
Without this table the inventory reports Scope 3 categories 1-7 as "not measured" (never as zero).

## 2. Platform stack (API, agent runtime, GHG state machine, usage table)
```bash
bash scripts/build_layer.sh                       # recent boto3 layer (bedrock-agentcore client)
cd infra && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
cdk deploy EsgPlatformStack -c apiKey="$(openssl rand -hex 24)"   # keep the key
```
CDK builds the container from `agentcore/Dockerfile` (context `esg-reporting-poc/`, ARM64). Outputs:
`PlatformApiUrl`, `PlatformFunctionUrl`, `AgentRuntimeArn`, `GhgStateMachineArn`, `UsageTableName`, `UsageMeterPolicyArn`.
Optional context: `-c allowedOrigin=https://your-app-domain`, `-c routingProfile=balanced|economy`.

## 3. Update the existing pipeline Lambdas
```bash
PII_TOKEN_SECRET="$(openssl rand -hex 32)" USAGE_TABLE=esg-llm-usage bash scripts/package_lambdas.sh
```
This updates `esg-section-gen`, `esg-validation`, `esg-athena-query`, `esg-assembly-doc` (shared modules bundled flat),
merges the new environment variables (never replaces them), and syncs templates and prompts to the KB bucket.
Then attach the managed policy `esg-usage-meter-write` (output `UsageMeterPolicyArn`) to the execution role of `esg-section-gen`.

## 4. Update the report state machine
Replace the definition of `ESGReportGenerationStateMachine` with `step_functions/esg_orchestrator.asl.json`
(a backup of the previous one is `esg_orchestrator_backup_v3_pre_agentcore.asl.json`). The change only adds fields.

## 5. Frontend
```bash
cd ../esg-chat-app-react && cp .env.example .env   # fill the three values from the CDK outputs
npm ci && npm run build
```
Set the same variables in Amplify (Environment variables) if you deploy through Amplify.

## 6. Smoke tests
```bash
API=<PlatformApiUrl>; KEY=<apiKey>
curl -s $API/health
curl -s -H "x-api-key: $KEY" "$API/compliance/readiness?year=2024" | head -c 400
curl -s -H "x-api-key: $KEY" "$API/ghg/inventory?year=2024" | head -c 400
curl -s -H "x-api-key: $KEY" -X POST $API/scenario -d '{"year":2024}' | head -c 400
aws lambda invoke --function-name esg-platform-api --payload '{"action":"regulatory_scan"}' --cli-binary-format raw-in-base64-out /dev/stdout
```
Then in the UI ask the assistant to "generate a GRI 305 report for 2024" and watch the Agent activity panel.

## Known limits and notes
- API Gateway HTTP APIs cut requests at 30 s; chat and scans use the Lambda Function URL (`VITE_AGENT_CHAT_URL`).
- The API key is bundled into the frontend: a demo gate. Use Cognito or IAM auth before real use.
- Regulatory sources in `platform_api/config/pspk_checklist.json` and peer scores in `config/peers.json` are illustrative.
- TKBI classification per sector is an assumption (`_shared/esg_domain.py`), not the official taxonomy mapping.
- Not built: feature #5 (data connectors to HR, core banking and utility systems).
- Pre-signed download links are stored in the ledger and expire after 1 hour; the UI re-reads the ledger on every refresh only while the link is valid.
