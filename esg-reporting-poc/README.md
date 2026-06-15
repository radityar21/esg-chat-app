# ESG Reporting POC

Automated ESG report generation using AWS Bedrock, Athena, and Step Functions.

## Project Structure

```
esg-reporting-poc/
├── config/
│   └── esg_config.yaml              # Central configuration
├── glue_jobs/
│   ├── glue_job_scope1_ghg.py       # Scope 1 GHG calculation
│   ├── glue_job_scope2_electricity.py # Scope 2 electricity emissions
│   ├── glue_job_scope3_pcaf.py      # Scope 3 PCAF financed emissions
│   └── glue_job_aggregation.py      # Aggregation layer (join all scopes)
├── sql/ddl/
│   ├── 01_create_databases.sql      # Glue database creation
│   ├── 02_raw_tables.sql            # Raw zone table DDL
│   ├── 03_curated_tables.sql        # Curated zone table DDL
│   └── 04_aggregated_tables.sql     # Aggregated zone table DDL
├── prompts/
│   ├── base_prompt.txt              # Universal generation rules
│   ├── overlay_gri305.txt           # GRI 305 framework overlay
│   ├── overlay_ifrs_s2.txt          # IFRS S2 framework overlay
│   ├── overlay_csrd_e1.txt          # CSRD/ESRS E1 framework overlay
│   └── overlay_ojk_pspk.txt         # OJK POJK 51/2017 overlay
├── templates/
│   ├── section_scope1.txt           # Scope 1 narrative template
│   ├── section_scope2.txt           # Scope 2 narrative template
│   ├── section_scope3_pcaf.txt      # Scope 3 PCAF narrative template
│   ├── section_summary.txt          # Executive summary template
│   ├── section_methodology.txt      # Methodology & assumptions template
│   └── section_targets.txt          # Targets & reduction template
├── lambda/
│   ├── validate_input/              # Lambda #1: Input validation
│   ├── athena_query/                # Lambda #2: Athena query executor
│   ├── section_gen/                 # Lambda #3: AI section generation (Bedrock)
│   ├── validation/                  # Lambda #4: Output validation (21 rules)
│   └── assembly_doc/               # Lambda #5: DOCX assembly
├── step_functions/
│   └── esg_orchestrator.asl.json    # Step Functions state machine definition
├── scripts/
│   ├── setup_account.sh             # D1: AWS account setup (IAM, S3, tags)
│   ├── generate_energy_data.py      # D2: Synthetic energy data generator
│   ├── generate_loan_portfolio.py   # D2: Synthetic loan portfolio generator
│   └── deploy_lambdas.sh            # Lambda deployment script
├── infra/
│   ├── app.py                       # CDK app entry point
│   ├── cdk.json                     # CDK configuration
│   ├── requirements.txt             # CDK dependencies
│   └── stacks/
│       └── esg_infra_stack.py       # Main CDK stack
├── tests/
│   ├── test_validate_input.py
│   ├── test_athena_query.py
│   └── test_validation.py
└── README.md
```

## Quick Start

1. **Setup AWS Account (D1):**
   ```bash
   chmod +x scripts/setup_account.sh
   ./scripts/setup_account.sh
   ```

2. **Generate Synthetic Data (D2):**
   ```bash
   python scripts/generate_energy_data.py
   python scripts/generate_loan_portfolio.py
   ```

3. **Run Athena DDL (D3):**
   Execute SQL files in `sql/ddl/` via Athena console or CLI.

4. **Deploy Infrastructure:**
   ```bash
   cd infra && pip install -r requirements.txt
   cdk deploy
   ```

## Frameworks Supported

| Framework | Overlay | Standard |
|-----------|---------|----------|
| GRI 305 | `overlay_gri305.txt` | GRI 305 Emissions 2016 |
| IFRS S2 | `overlay_ifrs_s2.txt` | IFRS S2 Climate-related Disclosures |
| CSRD E1 | `overlay_csrd_e1.txt` | ESRS E1 Climate Change |
| OJK PSPK | `overlay_ojk_pspk.txt` | POJK 51/2017 |

## Architecture

- **Data Layer:** S3 → Glue ETL → Athena (raw → curated → aggregated)
- **AI Layer:** Bedrock (Claude 3.5 Sonnet) + Knowledge Base (RAG)
- **Orchestration:** Step Functions → Lambda pipeline
- **Output:** DOCX report saved to S3

## Tags

All resources tagged with:
- `Project=ESG`
- `Env=POC`
- `Team=Sustainability`
