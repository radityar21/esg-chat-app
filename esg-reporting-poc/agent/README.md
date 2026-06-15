# Amazon Bedrock Agent — ESG Chat Assistant

AI-powered conversational assistant for ESG report generation, built on **Amazon Bedrock Agents** with **Claude 3.5 Sonnet**.

---

## 🎯 Overview

The ESG Chat Assistant enables users to:
- **Generate ESG reports** via natural language (e.g., "Generate a GRI 305 report for 2024")
- **Check report status** (e.g., "What's the status of execution abc123?")
- **Download reports** (e.g., "Give me the download link for my last report")
- **Query ESG knowledge base** (e.g., "What is PCAF?", "Explain Scope 3 emissions")

**Key Features:**
- Strict ESG-only scope (rejects off-topic questions)
- Markdown-formatted responses with emoji
- Integration with Step Functions orchestrator
- Knowledge base backed by ESG framework documents

---

## 📁 Files

```
agent/
├── agent_instructions.txt        # System prompt + guardrails
├── openapi_schema.json           # Agent tools (4 actions)
├── lambda_agent_tools/
│   └── handler.py                # Lambda backing agent tools
└── README.md                     # This file
```

---

## 🧠 Agent Configuration

### Foundation Model
- **Model:** `anthropic.claude-3-5-sonnet-20240620-v2:0`
- **Region:** `ap-southeast-1` (Singapore)
- **Temperature:** 0.7 (balanced creativity)

### Knowledge Base
- **Documents:** GRI 305, IFRS S2, CSRD/ESRS E1, OJK PSPK, PCAF methodology
- **Embedding Model:** Amazon Titan Embeddings v2
- **Vector Store:** Amazon OpenSearch Serverless

### Agent Tools (4 Actions)

| Tool | HTTP Method | Purpose |
|------|------------|---------|
| `generate_report` | POST | Start report generation (returns execution ID) |
| `check_status` | POST | Check report status (RUNNING/SUCCEEDED/FAILED) |
| `download_report` | POST | Get presigned S3 download URLs (DOCX + PPTX) |
| `list_available_data` | GET | List available years (2023, 2024) and frameworks |

---

## 📝 Agent Instructions

The agent follows strict guidelines defined in `agent_instructions.txt`:

### 1. Scope Guardrails
**ESG-Only Policy:**
- ONLY answer questions related to ESG, sustainability, climate reporting, GHG emissions, PCAF, GRI, IFRS, CSRD, OJK
- Reject off-topic questions with polite message:
  > "I'm specialized in ESG reporting and sustainability topics. That question is outside my scope. Can I help you with ESG reports instead?"

### 2. Response Formatting
- **Markdown:** Use `**bold**`, `#headers`, bullet lists
- **Emoji:** Add relevant icons (📊, 🌍, 💡, ✅, ⚠️)
- **Structure:** Short paragraphs, clear headings, numbered steps
- **Tone:** Professional but conversational

### 3. Report Generation Workflow
1. User asks: "Generate a GRI 305 report for 2024"
2. Agent calls `generate_report` tool
3. Agent returns execution ID: "Report generation started! ID: exec_abc123"
4. User asks: "What's the status?"
5. Agent calls `check_status` tool
6. Agent returns: "Your report is ready! Download: [link]"

### 4. Context Awareness
- Agent has access to knowledge base (ESG frameworks, PCAF methodology)
- Agent retrieves relevant context before answering technical questions
- Agent cites sources when referencing specific frameworks

---

## 🛠️ Setup Instructions

### Step 1: Create Bedrock Agent

**Console:**
1. Go to **Amazon Bedrock Console** → **Agents**
2. Click **Create Agent**
3. Name: `ESG-Report-Assistant`
4. Model: **Claude 3.5 Sonnet v2**
5. Instructions: Copy content from `agent_instructions.txt`

**CLI:**
```bash
aws bedrock-agent create-agent --agent-name ESG-Report-Assistant --foundation-model anthropic.claude-3-5-sonnet-20240620-v2:0 --instruction file://agent_instructions.txt --region ap-southeast-1
```

---

### Step 2: Deploy Lambda for Agent Tools

**Build:**
```bash
cd lambda_agent_tools
zip -r ../../../deploy/agent_tools.zip handler.py
```

**Deploy:**
```bash
aws lambda update-function-code --function-name esg-agent-tools --zip-file fileb://../../deploy/agent_tools.zip --region ap-southeast-1
```

**IAM Role:** Lambda needs:
- `states:StartExecution` (to trigger Step Functions)
- `states:DescribeExecution` (to check status)
- `s3:GetObject` (to generate presigned URLs)

---

### Step 3: Add Tools to Agent

**Console:**
1. Go to Agent → **Action Groups**
2. Click **Add Action Group**
3. Name: `report-generation-tools`
4. Action group type: **Define with API schemas**
5. Upload: `openapi_schema.json`
6. Lambda function: `esg-agent-tools`

**CLI:**
```bash
aws bedrock-agent create-agent-action-group --agent-id AGENT_ID --agent-version DRAFT --action-group-name report-generation-tools --action-group-executor lambda=arn:aws:lambda:ap-southeast-1:123456789012:function:esg-agent-tools --api-schema file://openapi_schema.json --region ap-southeast-1
```

---

### Step 4: Add Knowledge Base

**Console:**
1. Go to **Bedrock** → **Knowledge Bases**
2. Create knowledge base with S3 data source
3. Upload ESG framework PDFs to S3:
   - `s3://esg-knowledge-base/GRI_305_Standard.pdf`
   - `s3://esg-knowledge-base/IFRS_S2_Climate.pdf`
   - `s3://esg-knowledge-base/PCAF_Global_Standard.pdf`
   - `s3://esg-knowledge-base/CSRD_ESRS_E1.pdf`
   - `s3://esg-knowledge-base/OJK_PSPK_Regulation.pdf`
4. Associate knowledge base with agent

**CLI:**
```bash
aws bedrock-agent associate-agent-knowledge-base --agent-id AGENT_ID --knowledge-base-id KB_ID --description "ESG Framework Documentation" --region ap-southeast-1
```

---

### Step 5: Test Agent

**Console Test:**
1. Go to Agent → **Test**
2. Enter: "Generate a GRI 305 report for 2024"
3. Verify agent calls `generate_report` tool
4. Enter: "What is PCAF?"
5. Verify agent retrieves from knowledge base

**CLI Test:**
```bash
aws bedrock-agent-runtime invoke-agent --agent-id AGENT_ID --agent-alias-id TSTALIASID --session-id test-session-1 --input-text "Generate a GRI 305 report for 2024" --region ap-southeast-1
```

---

### Step 6: Create Alias & Deploy

**Console:**
1. Go to Agent → **Aliases**
2. Click **Create Alias**
3. Name: `production`
4. Associate with latest agent version

**CLI:**
```bash
aws bedrock-agent create-agent-alias --agent-id AGENT_ID --alias-name production --region ap-southeast-1
```

---

## 🔧 Agent Tools Details

### 1. generate_report

**Purpose:** Start ESG report generation pipeline

**Parameters:**
```json
{
  "reporting_year": 2024,           // Required: 2023 or 2024
  "framework": "GRI_305",           // Required: GRI_305, IFRS_S2, CSRD_ESRS_E1, OJK_PSPK, MULTI_FRAMEWORK
  "revenue_idr_billion": 92000      // Optional: default 92000 (IDR 92 Trillion)
}
```

**Response:**
```json
{
  "execution_arn": "arn:aws:states:...:execution:esg-orchestrator:exec_abc123",
  "execution_id": "exec_abc123",
  "status": "RUNNING",
  "estimated_time_minutes": "3-12"
}
```

**Lambda Logic:**
- Validates input
- Starts Step Functions execution
- Returns execution ID for status tracking

---

### 2. check_status

**Purpose:** Check report generation status

**Parameters:**
```json
{
  "execution_arn": "exec_abc123"    // Can be full ARN or short ID
}
```

**Response (RUNNING):**
```json
{
  "status": "RUNNING",
  "execution_id": "exec_abc123",
  "progress": "Generating sections 5/9"
}
```

**Response (SUCCEEDED):**
```json
{
  "status": "SUCCEEDED",
  "execution_id": "exec_abc123",
  "download_url": "https://s3.amazonaws.com/...",
  "download_url_pptx": "https://s3.amazonaws.com/...",
  "framework": "MULTI_FRAMEWORK",
  "reporting_year": 2024
}
```

**Response (FAILED):**
```json
{
  "status": "FAILED",
  "execution_id": "exec_abc123",
  "error": "Bedrock API throttled"
}
```

---

### 3. download_report

**Purpose:** Get presigned download URLs

**Parameters:**
```json
{
  "execution_arn": "exec_abc123"
}
```

**Response:**
```json
{
  "download_url": "https://esg-reporting-output-bucket.s3.amazonaws.com/...?X-Amz-Expires=3600",
  "download_url_pptx": "https://esg-reporting-output-bucket.s3.amazonaws.com/...?X-Amz-Expires=3600",
  "expires_in_seconds": 3600
}
```

**Note:** URLs expire after 1 hour

---

### 4. list_available_data

**Purpose:** Show available reporting years and frameworks

**Parameters:** None (GET request)

**Response:**
```json
{
  "available_years": [2023, 2024],
  "frameworks": [
    {
      "id": "GRI_305",
      "name": "GRI 305: Emissions",
      "sections": 5
    },
    {
      "id": "IFRS_S2",
      "name": "IFRS S2 Climate-related Disclosures",
      "sections": 4
    },
    {
      "id": "MULTI_FRAMEWORK",
      "name": "Comprehensive Multi-Framework Report",
      "sections": 9,
      "includes_pptx": true
    }
  ]
}
```

---

## 🧪 Testing Examples

### Example 1: Generate Report
**User:** "Generate a multi-framework ESG report for 2024"

**Agent Response:**
```
📊 **Report Generation Started!**

I've initiated the generation of a **MULTI_FRAMEWORK** ESG report for **2024**.

**Execution ID:** `exec_abc123`  
**Estimated Time:** 8-12 minutes  
**Status:** RUNNING

The report will include:
- 🌍 GRI 305 (Emissions)
- 📈 IFRS S2 (Climate Disclosures)
- 🇪🇺 CSRD/ESRS E1 (EU Sustainability)
- 🇮🇩 OJK PSPK (Indonesia Banking)
- 💼 PCAF Financed Emissions
- 📊 Double Materiality Analysis

**Outputs:**
- 📄 DOCX report (~40 pages)
- 📊 PPTX presentation (4 slides)

To check progress, ask me: "What's the status of exec_abc123?"
```

---

### Example 2: Check Status
**User:** "What's the status of exec_abc123?"

**Agent Response (RUNNING):**
```
⏳ **Report Generation in Progress**

**Execution ID:** exec_abc123  
**Status:** RUNNING  
**Progress:** Generating sections 6/9

Estimated completion: ~5 minutes

I'll notify you when it's ready!
```

**Agent Response (SUCCEEDED):**
```
✅ **Report Ready for Download!**

Your **MULTI_FRAMEWORK 2024** report has been successfully generated.

**📥 Downloads:**
- [Download DOCX Report](https://s3.amazonaws.com/...)
- [Download PPTX Presentation](https://s3.amazonaws.com/...)

**📊 Report Includes:**
- 42 pages of comprehensive ESG disclosures
- All 9 framework sections
- Data provenance tables
- Management sign-off page

Links expire in 1 hour. Need a fresh link? Just ask!
```

---

### Example 3: Knowledge Base Query
**User:** "What is PCAF?"

**Agent Response:**
```
💡 **PCAF (Partnership for Carbon Accounting Financials)**

PCAF is a **global collaboration** of financial institutions working to develop and implement a harmonized approach to assess and disclose the **greenhouse gas (GHG) emissions** associated with their **loans and investments** (financed emissions).

**Key Points:**
- 📊 **Standard for Scope 3 Category 15** (financed emissions)
- 🏦 Used by **banks, investors, and insurers** globally
- 📈 **Data quality scores** from 1 (best) to 5 (estimates)
- 🌍 Covers **7 asset classes** (corporate loans, mortgages, listed equity, etc.)

**PCAF in This System:**
- Our reports include PCAF-compliant financed emissions calculations
- Data quality scores are tracked and disclosed
- Sector-level breakdowns align with PCAF methodology

**Frameworks Using PCAF:**
- ✅ IFRS S2 (Climate-related Disclosures)
- ✅ GRI 305-3 (Scope 3 Emissions)
- ✅ CSRD/ESRS E1 (EU Sustainability Reporting)

Need a PCAF-compliant report? I can generate one for you! 📊
```

---

### Example 4: Off-Topic Query (Rejected)
**User:** "What is pCAF protein?"

**Agent Response:**
```
⚠️ **Outside My Scope**

I'm specialized in **ESG reporting and sustainability topics** (climate, emissions, PCAF methodology, GRI, IFRS, etc.).

That question appears to be about **biochemistry** (p300/CBP-associated factor protein), which is outside my area of expertise.

**I can help with:**
- 📊 Generating ESG reports
- 🌍 Explaining climate frameworks (GRI, IFRS, CSRD)
- 💼 PCAF financed emissions methodology
- 📈 ESG data analysis and metrics

Would you like to generate an ESG report or learn about sustainability topics?
```

---

## 🔐 Security & Access Control

### Agent Permissions (IAM Role)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:Retrieve"
      ],
      "Resource": [
        "arn:aws:bedrock:ap-southeast-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v2:0",
        "arn:aws:bedrock:ap-southeast-1:123456789012:knowledge-base/KB_ID"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:ap-southeast-1:123456789012:function:esg-agent-tools"
    }
  ]
}
```

### Lambda Tool Permissions
```json
{
  "Effect": "Allow",
  "Action": [
    "states:StartExecution",
    "states:DescribeExecution",
    "states:GetExecutionHistory",
    "s3:GetObject",
    "s3:PutObject"
  ],
  "Resource": [
    "arn:aws:states:ap-southeast-1:123456789012:stateMachine:esg-orchestrator",
    "arn:aws:states:ap-southeast-1:123456789012:execution:esg-orchestrator:*",
    "arn:aws:s3:::esg-reporting-output-bucket/*"
  ]
}
```

---

## 💰 Cost Estimates

| Component | Unit Cost | Usage per Session | Cost |
|-----------|----------|------------------|------|
| **Bedrock Agent (Claude 3.5 Sonnet)** | $3/MTok (input), $15/MTok (output) | ~5K input + 2K output | $0.045 |
| **Knowledge Base Retrieval** | $0.10 per 1K queries | 2 queries | $0.0002 |
| **Lambda (Agent Tools)** | $0.20 per 1M requests | 3 invocations | $0.0006 |
| **Total per Chat Session** | | | **~$0.05** |

**Note:** Report generation costs (~$0.12 per report) are separate from chat costs.

---

## 🛠️ Troubleshooting

### Agent Doesn't Call Tools
**Issue:** Agent says "I don't have that capability"

**Solution:**
1. Verify action group is attached to agent
2. Check `openapi_schema.json` is valid
3. Ensure Lambda has correct permissions
4. Test Lambda directly: `aws lambda invoke --function-name esg-agent-tools ...`

---

### Knowledge Base Not Retrieving
**Issue:** Agent doesn't answer framework questions

**Solution:**
1. Verify knowledge base is associated with agent
2. Check S3 data source has PDF documents
3. Sync knowledge base: **Bedrock Console** → **Knowledge Bases** → **Sync**
4. Test retrieval: **Knowledge Bases** → **Test**

---

### Agent Answers Off-Topic Questions
**Issue:** Agent answers non-ESG questions (e.g., "What is pCAF protein?")

**Solution:**
1. Update `agent_instructions.txt` with stricter guardrails
2. Redeploy agent: **Agents** → **Prepare**
3. Test with off-topic queries to verify rejection

**Latest Instructions (June 2026):**
- ✅ Reject all non-ESG questions
- ✅ Polite rejection message
- ✅ Redirect to ESG topics

---

### Markdown Not Rendering in Frontend
**Issue:** Agent responses show `**text**` instead of bold

**Solution:**
1. Frontend must parse markdown in `Chat.jsx`
2. Install: `npm install react-markdown`
3. Use: `<ReactMarkdown>{message.content}</ReactMarkdown>`

---

## 📊 Monitoring

### CloudWatch Logs
- **Agent invocations:** `/aws/bedrock/agents/AGENT_ID`
- **Lambda tools:** `/aws/lambda/esg-agent-tools`
- **Step Functions:** `/aws/vendedlogs/states/esg-orchestrator`

### Metrics to Track
- **Invocation count** — How many chat sessions?
- **Tool call success rate** — Are tools executing correctly?
- **Knowledge base retrieval** — How often is KB used?
- **Average response time** — Agent latency
- **Off-topic rejection rate** — Guardrail effectiveness

---

## 🔗 Related Documentation

- **Backend:** `../README.md`
- **Lambda Functions:** `../lambda/README.md`
- **Frontend Chat UI:** `../../esg-chat-app-react/README.md`
- **Root README:** `../../README.md`

---

**Maintained by:** Tokaicom Mitra Indonesia (Tokai Group)  
**Last Updated:** June 15, 2026
