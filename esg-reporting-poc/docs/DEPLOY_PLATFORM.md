# Deploying the ESG Intelligence platform (from an empty account, PowerShell)

Account `061039769766`, region `us-east-1`, one environment (prod). Backend with CDK, frontend on Amplify (GitHub, branch `main-agentcore`).
All commands run from `esg-reporting-poc\` unless stated. Stack order (each depends on the previous):

    EsgFoundationStack  ->  EsgNetworkStack + EsgDatabaseStack  ->  EsgDataStack  ->  EsgPlatformStack

## 0. One-time prerequisites
AWS CLI v2 (logged in), Python 3.12, Node 20, Git, `npm install -g aws-cdk`, `Set-ExecutionPolicy -Scope Process Bypass`.
Bedrock console > Model access: enable **Claude Sonnet 4.5**, **Claude Haiku 4.5** and **Titan Text Embeddings V2**.
Create the Amplify app (console, GitHub, repo `esg-chat-app`, branch `main-agentcore`) and note the App ID.
`cdk bootstrap aws://061039769766/us-east-1`. Docker is not needed.

```powershell
$ACCT = "061039769766"; $env:AWS_REGION = "us-east-1"
$APPID = "<AppID>"; $APP = "https://main-agentcore.$APPID.amplifyapp.com"
```

## 1. Build artifacts and CDK environment
```powershell
python scripts\build_all.py            # Lambda packages, python-docx layer, boto3/pg8000 layers, agent zip (needs internet, no Docker)
cd infra; python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; pip install boto3
cd ..
```
Re-run `build_all.py` after changing any Lambda or agent code, then `cdk deploy` the stack that owns it.

## 2. Foundation: buckets, catalog, ETL jobs, report Lambdas, state machine, Knowledge Base
```powershell
cd infra; cdk deploy EsgFoundationStack --app "python app.py"; cd ..
python scripts\apply_ddl.py            # Glue databases + Athena tables (13 statements)
$f = aws cloudformation describe-stacks --stack-name EsgFoundationStack --query "Stacks[0].Outputs" | ConvertFrom-Json
$KB = ($f | ? OutputKey -eq KnowledgeBaseId).OutputValue; $DS = ($f | ? OutputKey -eq KnowledgeBaseDataSourceId).OutputValue
python scripts\upload_kb_documents.py --kb-id $KB --data-source-id $DS     # uploads ~75 MB and waits for ingestion (10-20 min)
```
The Knowledge Base uses S3 Vectors (pay per use, no OpenSearch Serverless floor), Titan V2 embeddings, semantic chunking.

## 3. Network and database
```powershell
cd infra; cdk deploy EsgNetworkStack EsgDatabaseStack --app "python app.py"; cd ..     # RDS takes ~10 minutes
```

## 4. Source data and extract job
```powershell
aws s3 cp data\seed\rds "s3://esg-data-raw-$ACCT/seed/rds/" --recursive
cd infra; cdk deploy EsgDataStack --app "python app.py"; cd ..
'{"action":"init"}' | Set-Content p.json -Encoding ascii
aws lambda invoke --function-name esg-rds-seed --payload fileb://p.json --cli-binary-format raw-in-base64-out out.json; Get-Content out.json
'{"action":"load","reload":true}' | Set-Content p.json -Encoding ascii
aws lambda invoke --function-name esg-rds-seed --payload fileb://p.json --cli-binary-format raw-in-base64-out out.json; Get-Content out.json
```
Expected row counts: energy 5280, loans 4400, hr 2, scope3 16. Test one table without the agent:
```powershell
$SYNC = "arn:aws:states:us-east-1:${ACCT}:stateMachine:ESGDataSyncStateMachine"
'{"reporting_year":2024,"tables":["hr_metrics"]}' | Set-Content in.json -Encoding ascii
$ex = aws stepfunctions start-execution --state-machine-arn $SYNC --input file://in.json --query executionArn --output text
Start-Sleep 90; aws stepfunctions describe-execution --execution-arn $ex --query "{status:status,output:output}"
```

## 5. Platform: API, login, agent
```powershell
cd infra; cdk deploy EsgPlatformStack --app "python app.py" -c appUrl=$APP; cd ..
$o = aws cloudformation describe-stacks --stack-name EsgPlatformStack --query "Stacks[0].Outputs" | ConvertFrom-Json
$API = ($o | ? OutputKey -eq PlatformApiUrl).OutputValue; $POOL = ($o | ? OutputKey -eq CognitoUserPoolId).OutputValue
$CLIENT = ($o | ? OutputKey -eq CognitoClientId).OutputValue; $DOMAIN = ($o | ? OutputKey -eq CognitoDomain).OutputValue
```

## 6. Users and frontend
```powershell
$email = "you@company.com"
aws cognito-idp admin-create-user --user-pool-id $POOL --username $email --user-attributes Name=email,Value=$email Name=email_verified,Value=true --desired-delivery-mediums EMAIL
aws cognito-idp admin-add-user-to-group --user-pool-id $POOL --username $email --group-name admin
aws amplify update-app --app-id $APPID --environment-variables "VITE_PLATFORM_API_URL=$API,VITE_COGNITO_DOMAIN=$DOMAIN,VITE_COGNITO_CLIENT_ID=$CLIENT"
aws amplify start-job --app-id $APPID --branch-name main-agentcore --job-type RELEASE
```

## 7. First data run and smoke test
Sign in on the Amplify URL, open AI Assistant and ask: "Sync the 2024 data from the database" (loads the tables, then runs the
Scope 1/2/3 ETL), repeat for 2023, then "Generate a GRI 305 report for 2024".
`Invoke-RestMethod "$API/health"` returns `ok`; without a token every other route returns 401.

## Security and operations notes
- Users: no self-sign-up, password 12+ characters, optional MFA. Roles from the `admin` / `viewer` groups; unknown users get 403.
- Secrets: `esg/pii-token-secret` (created by the foundation stack, do not rotate casually), `esg/rds/master`, `esg/rds/reader`.
- Retention: logs 14 days; usage, chat-job tables 14 days (TTL); operational S3 prefixes (agent-ledger, executions, platform-cache, etl-reports) and Athena results 14 days. Generated reports, source data and compliance attestations are kept.
- Adaptive repair budgets are runtime variables (`SECTION_BUDGET_USD`, `RUN_BUDGET_USD`, `MAX_CORRECTION_ATTEMPTS`). Learned strategy statistics (`esg-agent-memory`) are kept.
- Buckets, the database and the Cognito pool are retained when a stack is deleted.

## Not verified in the build environment
Any `cdk deploy`; the Knowledge Base on S3 Vectors (ingestion, metadata filters); Glue jobs in isolated subnets; Lambdas inside the VPC reaching RDS;
the AgentCore runtime from a zip; Cognito redirects on the real domain; live Bedrock calls. Fix forward from the first error message.
