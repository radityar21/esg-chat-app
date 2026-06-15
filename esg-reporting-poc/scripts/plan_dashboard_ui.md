# Plan: Dashboard UI + History Endpoint

## Objective
Add a dashboard view to the ESG chat frontend showing execution history,
status overview, and quick actions. Chat remains primary interaction method.

## Critical Constraint
**NO changes to existing business logic pipeline.** All changes are:
- Frontend only (index.html)
- 1 new lightweight Lambda (read-only, no side effects)
- 1 new API Gateway route (GET /history)
- NO changes to: Step Functions, SectionGen, Validation, Assembly, Agent, KB

---

## Deliverable 1: New Lambda — `esg-history`

**Purpose:** Return list of recent Step Functions executions (read-only).

**Logic:**
```python
sfn_client.list_executions(
    stateMachineArn=STATE_MACHINE_ARN,
    maxResults=10,
    statusFilter="SUCCEEDED"  # or omit for all
)
```

**Response:**
```json
{
  "executions": [
    {
      "execution_id": "abc-123",
      "status": "SUCCEEDED",
      "start_time": "2026-06-10T10:00:00Z",
      "end_time": "2026-06-10T10:12:00Z",
      "duration_seconds": 720,
      "framework": "MULTI_FRAMEWORK",  // parsed from input
      "reporting_year": 2024,
      "download_url": "presigned..."  // only if SUCCEEDED
    }
  ],
  "total_succeeded": 5,
  "total_failed": 2,
  "total_running": 0
}
```

**Deployment:**
- Runtime: Python 3.11
- Timeout: 15s
- Memory: 128MB
- Role: ESGLambdaRole (already has states:ListExecutions permission)

---

## Deliverable 2: API Gateway Route — `GET /history`

- Add resource `/history` to existing API `olj4tuggm1`
- Method: GET, Authorization: NONE
- Lambda proxy integration → `esg-history`
- CORS enabled (same as /status)
- Deploy to `prod` stage

---

## Deliverable 3: Frontend Redesign — Dashboard + Chat

**Layout concept:**
```
┌─────────────────────────────────────────────────┐
│  Header (gradient, compact)                      │
├─────────────────────────────────────────────────┤
│                                                  │
│  [Dashboard View]              [Chat View]       │
│  ┌──────────────┐                               │
│  │ Stats Cards  │  ← shown on initial load      │
│  │ • Reports: 5 │                               │
│  │ • Last: 12m  │                               │
│  │ • Success: 80%│                              │
│  ├──────────────┤                               │
│  │ Recent List  │                               │
│  │ • Report 1 ↓ │                               │
│  │ • Report 2 ↓ │                               │
│  ├──────────────┤                               │
│  │ [Generate]   │ ← button transitions to chat  │
│  └──────────────┘                               │
│                                                  │
├─────────────────────────────────────────────────┤
│  Input bar (always visible)                      │
└─────────────────────────────────────────────────┘
```

**Behavior:**
1. On page load: fetch `/history` → render dashboard cards + recent reports list
2. User clicks "Generate Report" button OR types in input → transition to chat view
3. Chat view: same as current (messages + polling + download)
4. Toggle button to switch between dashboard / chat views
5. Dashboard auto-refreshes every 30s if there's a RUNNING execution

**Stats Cards:**
- Total Reports Generated (count of SUCCEEDED)
- Average Generation Time (mean duration)
- Last Report (timestamp + framework + download button)
- Active Executions (count of RUNNING — 0 or 1 typically)

**Recent Reports Table:**
- Columns: Date | Framework | Year | Duration | Status | Download
- Clickable download buttons (presigned URLs from Lambda)
- Max 10 most recent

---

## Deliverable 4: Fix Welcome Chip Text

Change chip texts to:
```javascript
// Before:
"Generate ESG report for 2024"  ← assumes year
"What data is available?"        ← triggers broken tool

// After:
"I want to generate a report"   ← agent asks year/framework
"What frameworks are supported?" ← agent answers from instructions, no tool call
"Check status"                   ← works as-is
```

---

## Safety Checks — NO Business Logic Impact

| Component | Change? | Impact Assessment |
|-----------|---------|-------------------|
| Step Functions ASL | ❌ NO | Not touched |
| esg-section-gen | ❌ NO | Not touched |
| esg-athena-query | ❌ NO | Not touched |
| esg-assembly-doc | ❌ NO | Not touched |
| esg-validation | ❌ NO | Not touched |
| esg-validate-input | ❌ NO | Not touched |
| esg-agent-tools | ❌ NO | Not touched |
| esg-filter-sections | ❌ NO | Not touched |
| Bedrock Agent | ❌ NO | Not touched |
| Knowledge Base | ❌ NO | Not touched |
| Glue ETL jobs | ❌ NO | Not touched |
| S3 data buckets | ❌ NO | Not touched |
| **esg-history (NEW)** | ✅ NEW | Read-only Lambda, no side effects |
| **API Gateway /history** | ✅ NEW | GET endpoint, read-only |
| **Frontend index.html** | ✅ MODIFIED | UI only, same API contracts |

---

## Deploy Order

1. Create Lambda `esg-history` (code + deploy)
2. Add API Gateway route `/history` (same pattern as /status)
3. Update `index.html` (dashboard + chips + design)
4. Deploy frontend to Amplify
5. Test: page load shows dashboard with history

---

## Timeline Estimate

| Task | Effort |
|------|--------|
| Lambda esg-history | 15 min |
| API Gateway route | 10 min |
| Frontend redesign | 30 min |
| Testing | 10 min |
| **Total** | **~65 min** |

---

## Future Enhancements (NOT in this scope)

- Real-time WebSocket updates (EventBridge → WebSocket API)
- Report comparison view (diff between years)
- Cost tracking per execution (CloudWatch metrics)
- User authentication (Cognito)


---

## Deliverable 5: Fix `list_available_data` + Reference Documents Feature

### 5A: Fix httpMethod Bug in Agent Tools Lambda

**Problem:** `_response()` function hardcodes `"httpMethod": "POST"` but agent invokes `list_available_data` via GET → mismatch → `dependencyFailedException`.

**Fix:** 1 line change in `agent/lambda_agent_tools/handler.py`:

```python
# Before:
"httpMethod": "POST",

# After:
"httpMethod": evt.get("httpMethod", "POST"),
```

This echoes back whatever method the agent used. No other side effects.

### 5B: Upgrade `list_available_data` to Dynamic S3 Listing

**Current:** Returns hardcoded string "2023 and 2024 available."

**New:** Lambda queries S3 to list actual available data:

```python
def _list_available_data():
    """List years with available data by checking S3."""
    available_years = set()
    
    # Check aggregated bucket for available years
    response = s3_client.list_objects_v2(
        Bucket="esg-data-aggregated-061039769766",
        Prefix="aggregated/ghg_summary_annual/reporting_year=",
        Delimiter="/"
    )
    for prefix in response.get("CommonPrefixes", []):
        # Extract year from "aggregated/ghg_summary_annual/reporting_year=2024/"
        year = prefix["Prefix"].split("=")[-1].rstrip("/")
        available_years.add(year)
    
    # List KB reference documents
    kb_response = s3_client.list_objects_v2(
        Bucket="esg-kb-documents-061039769766",
        Prefix="",
        Delimiter="/"
    )
    kb_folders = [p["Prefix"].rstrip("/") for p in kb_response.get("CommonPrefixes", [])]
    
    result = f"Available Data:\n\n"
    result += f"Reporting Years: {', '.join(sorted(available_years))}\n\n"
    result += f"Reference Document Categories:\n"
    for folder in kb_folders:
        result += f"- {folder}\n"
    result += f"\nFrameworks: GRI 305, IFRS S2, CSRD/ESRS E1, OJK PSPK, MULTI_FRAMEWORK"
    
    return _response(result)
```

### 5C: New API Endpoint — `GET /documents`

**Purpose:** Frontend calls this to list available reference documents in KB bucket (for dashboard display).

**Lambda:** `esg-documents-list` (or extend `esg-history` Lambda with a `?type=documents` param)

**Logic:**
```python
def list_documents():
    """List all reference documents in KB bucket with metadata."""
    documents = []
    
    # List all files in KB bucket (skip prompts/templates)
    paginator = s3_client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket="esg-kb-documents-061039769766"):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            # Skip prompts/templates (internal, not reference docs)
            if key.startswith("prompts/"):
                continue
            if key.endswith(".metadata.json"):
                continue
            documents.append({
                "key": key,
                "category": key.split("/")[0],  # e.g., "ifrs", "gri", "benchmarks"
                "filename": key.split("/")[-1],
                "size_kb": round(obj["Size"] / 1024, 1),
                "last_modified": obj["LastModified"].isoformat(),
            })
    
    return {
        "documents": documents,
        "total_count": len(documents),
    }
```

**Response example:**
```json
{
  "documents": [
    {"key": "ifrs/IFRS_S2_Climate_Disclosures_2023.pdf", "category": "ifrs", "filename": "IFRS_S2_Climate_Disclosures_2023.pdf", "size_kb": 289.6},
    {"key": "ifrs/IFRS_S2_SASB_Financials_Sector.pdf", "category": "ifrs", "filename": "IFRS_S2_SASB_Financials_Sector.pdf", "size_kb": 156.2},
    {"key": "gri/GRI_305_2016.pdf", "category": "gri", "filename": "GRI_305_2016.pdf", "size_kb": 142.8},
    {"key": "benchmarks/benchmarks_environment_banking_id.md", "category": "benchmarks", "filename": "benchmarks_environment_banking_id.md", "size_kb": 8.3},
    ...
  ],
  "total_count": 12
}
```

### 5D: Frontend — Reference Documents Panel

**In dashboard view, show a "Reference Library" section:**

```
┌─────────────────────────────────────┐
│ 📚 Reference Library                │
├─────────────────────────────────────┤
│ ┌─────────┐ ┌─────────┐ ┌────────┐│
│ │ GRI 305 │ │ IFRS S2 │ │Benchmk ││
│ │ 2 docs  │ │ 2 docs  │ │ 5 docs ││
│ └─────────┘ └─────────┘ └────────┘│
│                                     │
│ Click to ask about any document:    │
│ • GRI_305_2016.pdf        [Ask →]  │
│ • IFRS_S2_Climate_2023    [Ask →]  │
│ • Benchmark Environment   [Ask →]  │
│ • Benchmark Social        [Ask →]  │
└─────────────────────────────────────┘
```

**Behavior:**
- On page load: fetch `/documents` → render category cards + file list
- User clicks [Ask →] on a document → transition to chat → auto-send:
  `"Tell me about the key requirements in {document_name}"`
- Agent answers from KB via RAG (existing capability, no new backend needed)
- This combines list (visual) + content query (chat/RAG) in one flow

### 5E: Updated Dashboard Quick Actions

```javascript
// Dashboard buttons/cards
const QUICK_ACTIONS = [
    { icon: "📄", label: "Generate Report", action: () => quickSend("I want to generate a report") },
    { icon: "📚", label: "Reference Docs", action: () => showDocumentsPanel() },
    { icon: "🔍", label: "Check Status", action: () => quickSend("Check status") },
    { icon: "📊", label: "Ask about ESG", action: () => quickSend("What ESG frameworks do you support?") },
];
```

---

## Safety Check — Deliverable 5

| Component | Change? | Impact |
|-----------|---------|--------|
| esg-agent-tools | ✅ MODIFY (1 line httpMethod fix + S3 list logic) | Minimal — fixes existing bug, adds read-only S3 list |
| API Gateway | ✅ NEW route `/documents` | Read-only, no auth |
| Lambda (new or extend) | ✅ `esg-history` extended OR new `esg-documents-list` | Read-only S3 list |
| Frontend | ✅ MODIFY | UI only — adds documents panel + click-to-ask flow |
| Bedrock Agent | ❌ NO | Agent already answers from KB, no change needed |
| Step Functions | ❌ NO | Not touched |
| SectionGen/Validation/Assembly | ❌ NO | Not touched |

---

## Updated Deploy Order (All Deliverables)

1. Create Lambda `esg-history` (Deliverable 1)
2. Extend `esg-history` to handle `/documents` query OR create separate `esg-documents-list` (Deliverable 5C)
3. Add API routes: `/history` + `/documents` (Deliverables 2 + 5C)
4. Fix `esg-agent-tools` httpMethod + S3 list (Deliverable 5A + 5B) — deploy Lambda
5. Update `index.html` — dashboard + documents panel + chips (Deliverables 3 + 4 + 5D + 5E)
6. Deploy frontend to Amplify
7. Test full flow

