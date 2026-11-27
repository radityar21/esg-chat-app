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

# Platform stack. Needs: -c appUrl=https://<branch>.<amplify-app-id>.amplifyapp.com  (the exact origin of the frontend)
_app_url = app.node.try_get_context("appUrl")
if _app_url:
    if not str(_app_url).startswith("https://") or str(_app_url).rstrip("/").count("/") > 2:
        raise SystemExit("appUrl must be an https origin without a path, e.g. https://main-agentcore.d1abc.amplifyapp.com")
    EsgPlatformStack(app, "EsgPlatformStack", env=cdk.Environment(account=app.node.try_get_context("account") or __import__("os").environ.get("CDK_DEFAULT_ACCOUNT"), region="us-east-1"),
                     app_url=str(_app_url), dev_origin=app.node.try_get_context("devOrigin"),
                     routing_profile=app.node.try_get_context("routingProfile") or "quality")

app.synth()
