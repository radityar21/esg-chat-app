#!/usr/bin/env python3
# =============================================================================
# ESG Reporting POC - CDK App Entry Point
# =============================================================================

import aws_cdk as cdk
from stacks.esg_infra_stack import EsgInfraStack
from stacks.platform_stack import EsgPlatformStack
from stacks.network_stack import EsgNetworkStack
from stacks.database_stack import EsgDatabaseStack
from stacks.data_stack import EsgDataStack

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

# Source database path: deploy in this order  EsgNetworkStack -> EsgDatabaseStack -> EsgDataStack
_env = cdk.Environment(account=app.node.try_get_context("account") or __import__("os").environ.get("CDK_DEFAULT_ACCOUNT"), region="us-east-1")
if _env.account:
    _net = EsgNetworkStack(app, "EsgNetworkStack", env=_env)
    _db = EsgDatabaseStack(app, "EsgDatabaseStack", env=_env, vpc=_net.vpc, db_sg=_net.db_sg)
    EsgDataStack(app, "EsgDataStack", env=_env, vpc=_net.vpc, glue_sg=_net.glue_sg, tools_sg=_net.tools_sg, db=_db.db,
                 master_secret=_db.master_secret, reader_secret=_db.reader_secret)

# Platform stack. Needs: -c appUrl=https://<branch>.<amplify-app-id>.amplifyapp.com  (the exact origin of the frontend)
_app_url = app.node.try_get_context("appUrl")
if _app_url:
    if not str(_app_url).startswith("https://") or str(_app_url).rstrip("/").count("/") > 2:
        raise SystemExit("appUrl must be an https origin without a path, e.g. https://main-agentcore.d1abc.amplifyapp.com")
    EsgPlatformStack(app, "EsgPlatformStack", env=cdk.Environment(account=app.node.try_get_context("account") or __import__("os").environ.get("CDK_DEFAULT_ACCOUNT"), region="us-east-1"),
                     app_url=str(_app_url), dev_origin=app.node.try_get_context("devOrigin"),
                     routing_profile=app.node.try_get_context("routingProfile") or "quality",
                     agent_packaging=app.node.try_get_context("agentPackaging") or "zip")

app.synth()
