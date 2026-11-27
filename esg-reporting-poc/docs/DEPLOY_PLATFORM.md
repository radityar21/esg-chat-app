# Deploying the ESG Intelligence platform (production, PowerShell)

Single environment (`prod`) in account `061039769766`, region `us-east-1`. Frontend on Amplify Hosting (GitHub, branch
`main-agentcore`), backend by CDK. Run commands from `esg-reporting-poc\` unless stated.

## 0. One-time prerequisites (console)
1. **Bedrock model access** for Claude Sonnet 4.5 and Haiku 4.5 (Bedrock console > Model access).
2. **CDK bootstrap**: `cdk bootstrap aws://061039769766/us-east-1`.
3. **Docker Desktop** with buildx/QEMU (the AgentCore image is ARM64).
4. **Amplify app**: Amplify console > Create app > GitHub > repository `esg-chat-app`, branch `main-agentcore`.
   Install the Amplify GitHub App when asked. Leave the monorepo "app root" empty (the root `amplify.yml` handles it).
   Do not deploy yet; note the app id and the branch URL `https://main-agentcore.<appId>.amplifyapp.com`.

## 1. Source database (network, RDS, extract job)
Three stacks, deployed in this order. The database is PostgreSQL 16 (db.t4g.small, single AZ, encrypted, TLS only, 7-day
backups, deletion protection) in isolated subnets without NAT.
```powershell
$ACCT = "061039769766"; $env:AWS_REGION = "us-east-1"
New-Item -ItemType Directory -Force build\pglayer\python | Out-Null
python -m pip install --upgrade --target build\pglayer\python "pg8000>=1.31"
cd infra; python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
cdk deploy EsgNetworkStack EsgDatabaseStack --app "python app.py"      # RDS takes about 10 minutes
cd ..
aws s3 cp data/seed/rds "s3://esg-data-raw-$ACCT/seed/rds/" --recursive   # synthetic data used as the "database" content
cd infra; cdk deploy EsgDataStack --app "python app.py"; cd ..
```
Create the schema, the read-only user and load the data (the Lambda runs inside the VPC):
```powershell
'{"action":"init"}' | Set-Content p.json -Encoding ascii
aws lambda invoke --function-name esg-rds-seed --payload fileb://p.json --cli-binary-format raw-in-base64-out out.json; Get-Content out.json
'{"action":"load","reload":true}' | Set-Content p.json -Encoding ascii
aws lambda invoke --function-name esg-rds-seed --payload fileb://p.json --cli-binary-format raw-in-base64-out out.json; Get-Content out.json
```
Test the extract without the agent:
```powershell
$SYNC = "arn:aws:states:us-east-1:${ACCT}:stateMachine:ESGDataSyncStateMachine"
aws stepfunctions start-execution --state-machine-arn $SYNC --input '{\"reporting_year\":2024,\"tables\":[\"hr_metrics\"]}'
```
Demonstrate the agent's triage: plant a problem, ask the assistant to "sync the 2024 data from the database", then restore.
```powershell
'{"action":"inject","kind":"rename_column"}' | Set-Content p.json -Encoding ascii   # blocking: contract violation on hr_metrics
aws lambda invoke --function-name esg-rds-seed --payload fileb://p.json --cli-binary-format raw-in-base64-out out.json
'{"action":"reset"}' | Set-Content p.json -Encoding ascii                          # drops the tables and reloads clean data
aws lambda invoke --function-name esg-rds-seed --payload fileb://p.json --cli-binary-format raw-in-base64-out out.json
```
(`kind":"range"` plants a warning only: the load goes ahead and the note asks the data owner to confirm.)

## 2. Platform stack
```powershell
New-Item -ItemType Directory -Force build\layer\python | Out-Null
python -m pip install --upgrade --target build\layer\python "boto3>=1.40"
cd infra; python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
$APP = "https://main-agentcore.<appId>.amplifyapp.com"        # exact origin from step 0.4
cdk deploy EsgPlatformStack --app "python app.py" -c appUrl=$APP    # add -c devOrigin=http://localhost:5173 for local dev
cd ..
aws cloudformation describe-stacks --stack-name EsgPlatformStack --query "Stacks[0].Outputs" --output table
```
The stack creates: Cognito user pool (admin-created users, optional TOTP MFA), JWT-protected HTTP API, platform and trigger
Lambdas, usage and chat-job tables (14-day TTL), the strategy-memory table, PII secret, Bedrock guardrail, GHG state machine, AgentCore runtime,
EventBridge rules and a dead-letter queue.

## 3. Existing pipeline Lambdas, policies, lifecycle
```powershell
$o = aws cloudformation describe-stacks --stack-name EsgPlatformStack --query "Stacks[0].Outputs" | ConvertFrom-Json
$secret = ($o | ? OutputKey -eq PiiSecretArn).OutputValue
$policy = ($o | ? OutputKey -eq PipelineExtrasPolicyArn).OutputValue
$env:PII_TOKEN_SECRET_ARN = $secret; $env:USAGE_TABLE = "esg-llm-usage"
wsl bash scripts/package_lambdas.sh          # updates the 4 Lambdas, merges env vars, syncs templates/prompts/data
$role = (aws lambda get-function-configuration --function-name esg-section-gen --query Role --output text).Split('/')[-1]
aws iam attach-role-policy --role-name $role --policy-arn $policy
python scripts/apply_lifecycle.py            # 14-day expiry for ledger, executions, cache (keeps existing rules)
```

## 4. Report state machine
```powershell
$SM = "arn:aws:states:us-east-1:061039769766:stateMachine:ESGReportGenerationStateMachine"
aws stepfunctions describe-state-machine --state-machine-arn $SM --query definition --output text | Out-File sm_backup.json -Encoding utf8
aws stepfunctions update-state-machine --state-machine-arn $SM --definition file://step_functions/esg_orchestrator.asl.json
```

## 5. Users
```powershell
$pool = ($o | ? OutputKey -eq CognitoUserPoolId).OutputValue
aws cognito-idp admin-create-user --user-pool-id $pool --username someone@company.com --user-attributes Name=email,Value=someone@company.com Name=email_verified,Value=true --desired-delivery-mediums EMAIL
aws cognito-idp admin-add-user-to-group --user-pool-id $pool --username someone@company.com --group-name admin   # or viewer
```
A user without a group can sign in but every API call returns 403.

## 6. Amplify environment and release
```powershell
$appId = "<appId>"
$vars = @{
  VITE_PLATFORM_API_URL  = ($o | ? OutputKey -eq PlatformApiUrl).OutputValue
  VITE_COGNITO_DOMAIN    = ($o | ? OutputKey -eq CognitoDomain).OutputValue
  VITE_COGNITO_CLIENT_ID = ($o | ? OutputKey -eq CognitoClientId).OutputValue
}
$pairs = ($vars.GetEnumerator() | % { "$($_.Key)=$($_.Value)" }) -join ","
aws amplify update-app --app-id $appId --environment-variables $pairs
aws amplify start-job --app-id $appId --branch-name main-agentcore --job-type RELEASE
```
Every push to `main-agentcore` redeploys the frontend. `.github/workflows/ci.yml` runs tests, CDK synth and the frontend build.

## 7. Smoke tests
```powershell
$API = ($vars.VITE_PLATFORM_API_URL)
Invoke-RestMethod "$API/health"                                   # {"ok": true}
try { Invoke-RestMethod "$API/portfolio" } catch { $_.Exception.Response.StatusCode }   # 401 without a token
```
Then sign in on the Amplify URL: Portfolio, Compliance and GHG pages show the "Live · AWS" badge; the assistant answers;
ask it to generate a GRI 305 report for 2024 and follow the timeline in Agent activity.

## Security and operations notes
- Users: no self-sign-up; password 12+ characters; MFA optional (enable per user in Cognito).
- API: JWT authorizer on every route except `/health`; roles from the `admin` / `viewer` groups; stage throttle 30 req/s, burst 60.
- Secrets: PII pseudonym key in Secrets Manager (`esg/pii-token-secret`). Do not rotate it casually: existing tokens would change.
- IAM: Bedrock access is limited to the Claude 4.5 models; runtime S3 write is limited to the output bucket.
- Adaptive repair: budgets and ceiling are runtime environment variables (`SECTION_BUDGET_USD`, `RUN_BUDGET_USD`, `MAX_CORRECTION_ATTEMPTS`); the learned strategy statistics (`esg-agent-memory`) are kept (no TTL, retained on stack deletion).
- Retention: Lambda/runtime logs 14 days; usage and chat-job tables 14 days (TTL); ledger/executions/cache expire after 14 days.
  Generated reports and compliance attestations/alerts are NOT expired.
- Chat prompts are never stored; only the answer is kept for 14 days.
- No CloudWatch alarms or dashboards (decision). Traces: Lambda X-Ray and AgentCore OpenTelemetry stay on.
- Not verified in the build environment: Docker image build, `cdk deploy`, Cognito hosted-UI redirect with your real domain,
  runtime log-group naming (`/aws/bedrock-agentcore/runtimes/<id>-DEFAULT`), live AWS calls.

## Known limits
- Regulatory sources and peer scores are illustrative; the TKBI split per sector is an assumption.
- Source database: the Gateway-exposed tool path is not used; the agent calls `esg-data-tools` directly (the Lambda can become an AgentCore Gateway target later).
- Glue in isolated subnets with a Secrets Manager endpoint and `JDBC_ENFORCE_SSL` was configured from the documentation and has not been run; check the first Glue run log.
