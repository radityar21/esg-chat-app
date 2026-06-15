# ESG Chat App — Deployment Guide

## Architecture
```
Browser (index.html) → API Gateway (POST /chat) → Lambda (proxy) → Bedrock Agent
```

## Prerequisites
- Bedrock Agent `MBERNIQMBG` deployed and working
- Agent Alias `QIXEJW2TN6` (esg-report-agent-v2)
- `ESGLambdaRole` with Bedrock Agent Runtime permissions

---

## Step 1: Deploy Backend Lambda

```cmd
cd bedrock-agentcore-solution
powershell Compress-Archive -Path esg-chat-app\backend\handler.py -DestinationPath deploy\chat_proxy.zip -Force
aws s3 cp deploy\chat_proxy.zip s3://esg-data-raw-061039769766/lambda-code/chat_proxy.zip
aws lambda create-function --function-name esg-chat-proxy --runtime python3.11 --handler handler.lambda_handler --role arn:aws:iam::061039769766:role/ESGLambdaRole --code S3Bucket=esg-data-raw-061039769766,S3Key=lambda-code/chat_proxy.zip --timeout 60 --memory-size 256 --region us-east-1 --tags Project=ESG,Env=POC,Team=Sustainability
```

## Step 2: Add Bedrock Agent Runtime Permission to Lambda Role

```cmd
aws iam put-role-policy --role-name ESGLambdaRole --policy-name ESGLambdaBedrockAgentRuntime --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"bedrock:InvokeAgent\"],\"Resource\":\"arn:aws:bedrock:us-east-1:061039769766:agent-alias/MBERNIQMBG/*\"}]}"
```

## Step 3: Create API Gateway

```cmd
REM Create REST API
aws apigateway create-rest-api --name "ESG-Chat-API" --region us-east-1
```

Note the `id` from output (e.g., `abc123def`). Then:

```cmd
REM Get root resource ID
aws apigateway get-resources --rest-api-id {API_ID} --region us-east-1

REM Create /chat resource
aws apigateway create-resource --rest-api-id {API_ID} --parent-id {ROOT_ID} --path-part chat --region us-east-1

REM Create POST method
aws apigateway put-method --rest-api-id {API_ID} --resource-id {CHAT_ID} --http-method POST --authorization-type NONE --region us-east-1

REM Create OPTIONS method (CORS)
aws apigateway put-method --rest-api-id {API_ID} --resource-id {CHAT_ID} --http-method OPTIONS --authorization-type NONE --region us-east-1

REM Integration (POST → Lambda)
aws apigateway put-integration --rest-api-id {API_ID} --resource-id {CHAT_ID} --http-method POST --type AWS_PROXY --integration-http-method POST --uri "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:061039769766:function:esg-chat-proxy/invocations" --region us-east-1

REM Integration (OPTIONS → Mock for CORS)
aws apigateway put-integration --rest-api-id {API_ID} --resource-id {CHAT_ID} --http-method OPTIONS --type MOCK --request-templates "{\"application/json\": \"{\\\"statusCode\\\": 200}\"}" --region us-east-1

REM Deploy API
aws apigateway create-deployment --rest-api-id {API_ID} --stage-name prod --region us-east-1

REM Allow API Gateway to invoke Lambda
aws lambda add-permission --function-name esg-chat-proxy --statement-id APIGatewayInvoke --action lambda:InvokeFunction --principal apigateway.amazonaws.com --region us-east-1
```

Your API URL will be: `https://{API_ID}.execute-api.us-east-1.amazonaws.com/prod`

## Step 4: Update Frontend

Edit `frontend/index.html` — replace `REPLACE_WITH_API_GATEWAY_URL` with:
```
https://{API_ID}.execute-api.us-east-1.amazonaws.com/prod
```

## Step 5: Host Frontend

**Option A: S3 Static Website (simplest)**
```cmd
aws s3 mb s3://esg-chat-frontend-061039769766 --region us-east-1
aws s3 website s3://esg-chat-frontend-061039769766 --index-document index.html
aws s3 cp esg-chat-app\frontend\index.html s3://esg-chat-frontend-061039769766/index.html --content-type text/html

REM Make public (for demo only)
aws s3api put-bucket-policy --bucket esg-chat-frontend-061039769766 --policy "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"PublicRead\",\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"s3:GetObject\",\"Resource\":\"arn:aws:s3:::esg-chat-frontend-061039769766/*\"}]}"
aws s3api delete-public-access-block --bucket esg-chat-frontend-061039769766
```

Frontend URL: `http://esg-chat-frontend-061039769766.s3-website-us-east-1.amazonaws.com`

**Option B: Amplify Hosting (if preferred)**
```cmd
REM Install Amplify CLI, init, and deploy — or just drag-and-drop frontend/ folder in Amplify console
```

**Option C: Just open index.html locally**
After updating API_URL, double-click `frontend/index.html` in browser. Works for demo.

---

## Quick Test

After deployment, open frontend URL and type:
```
I want to generate an ESG report
```

Agent should respond asking for year → framework → revenue → then trigger pipeline.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| CORS error in browser | Check API Gateway OPTIONS method returns proper headers |
| "Access denied" from Lambda | Check `bedrock:InvokeAgent` permission on role |
| Agent not responding | Check agent is Prepared with alias QIXEJW2TN6 |
| Timeout | Increase Lambda timeout (Bedrock Agent can take 10-30s) |
