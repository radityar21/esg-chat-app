#!/usr/bin/env python3
# =============================================================================
# ESG Reporting POC - CDK App Entry Point
# =============================================================================

import aws_cdk as cdk
from stacks.esg_infra_stack import EsgInfraStack

app = cdk.App()

EsgInfraStack(app, "EsgReportingPocStack",
    env=cdk.Environment(
        region="us-east-1"  # N. Virginia
    ),
    tags={
        "Project": "ESG",
        "Env": "POC",
        "Team": "Sustainability"
    }
)

app.synth()
