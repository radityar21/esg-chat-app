#!/usr/bin/env python3
# =============================================================================
# ESG Reporting POC - CDK App Entry Point
# =============================================================================

import aws_cdk as cdk
from stacks.esg_infra_stack import EsgInfraStack
from stacks.platform_stack import EsgPlatformStack

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

# Platform stack (AgentCore orchestrator, platform API, GHG inventory, FinOps). Needs: -c apiKey=<secret>
_env = cdk.Environment(account=app.node.try_get_context("account") or __import__("os").environ.get("CDK_DEFAULT_ACCOUNT"), region="us-east-1")
_api_key = app.node.try_get_context("apiKey")
if _api_key or app.node.try_get_context("platform"):
    if not _api_key or len(str(_api_key)) < 16:
        raise SystemExit("EsgPlatformStack needs -c apiKey=<at least 16 characters>")
    EsgPlatformStack(app, "EsgPlatformStack", env=_env, api_key=str(_api_key),
                     allowed_origin=app.node.try_get_context("allowedOrigin") or "*",
                     routing_profile=app.node.try_get_context("routingProfile") or "quality")

app.synth()
