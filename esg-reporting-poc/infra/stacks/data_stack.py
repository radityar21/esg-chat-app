"""Data pipeline from the source database: Glue extract job with data contracts, the sync state machine,
and the two Lambdas that live in the VPC (seed loader for the demo data, read-only tools for the agent)."""

from __future__ import annotations

from pathlib import Path

from aws_cdk import CfnOutput, Duration, IgnoreMode, Stack, Tags, aws_ec2 as ec2, aws_glue as glue, aws_iam as iam, aws_lambda as _lambda, aws_logs as logs
from aws_cdk import aws_rds as rds, aws_s3_assets as s3_assets, aws_secretsmanager as sm, aws_stepfunctions as sfn
from constructs import Construct

POC = Path(__file__).resolve().parents[2]
JOB = "esg-extract-rds"
SYNC_SM = "ESGDataSyncStateMachine"
CONNECTION = "esg-source-db"


class EsgDataStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, vpc: ec2.IVpc, glue_sg: ec2.ISecurityGroup, tools_sg: ec2.ISecurityGroup,
                 db: rds.IDatabaseInstance, master_secret: sm.ISecret, reader_secret: sm.ISecret, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        Tags.of(self).add("Project", "ESG")
        acct, region = self.account, self.region
        raw_bucket, out_bucket = f"esg-data-raw-{acct}", f"esg-output-reports-{acct}"
        subnet = vpc.isolated_subnets[0]

        # ── Glue: connection, role, job ─────────────────────────────────────────────────────────
        conn = glue.CfnConnection(self, "SourceDbConnection", catalog_id=acct, connection_input=glue.CfnConnection.ConnectionInputProperty(
            name=CONNECTION, connection_type="JDBC",
            connection_properties={"JDBC_CONNECTION_URL": f"jdbc:postgresql://{db.db_instance_endpoint_address}:{db.db_instance_endpoint_port}/esgdb",
                                   "SECRET_ID": reader_secret.secret_name, "JDBC_ENFORCE_SSL": "true"},
            physical_connection_requirements=glue.CfnConnection.PhysicalConnectionRequirementsProperty(
                availability_zone=subnet.availability_zone, subnet_id=subnet.subnet_id, security_group_id_list=[glue_sg.security_group_id])))
        script = s3_assets.Asset(self, "ExtractScript", path=str(POC / "glue_jobs" / "esg_extract_rds.py"))
        contracts = s3_assets.Asset(self, "ContractsModule", path=str(POC / "glue_jobs" / "esg_contracts.py"))
        role = iam.Role(self, "ExtractRole", assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
                        managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole")])
        script.grant_read(role)
        contracts.grant_read(role)
        reader_secret.grant_read(role)
        role.add_to_policy(iam.PolicyStatement(actions=["s3:PutObject", "s3:DeleteObject", "s3:GetObject", "s3:ListBucket"],
                                               resources=[f"arn:aws:s3:::{raw_bucket}", f"arn:aws:s3:::{raw_bucket}/raw/*"]))
        role.add_to_policy(iam.PolicyStatement(actions=["s3:PutObject"], resources=[f"arn:aws:s3:::{out_bucket}/etl-reports/*"]))
        job = glue.CfnJob(
            self, "ExtractJob", name=JOB, role=role.role_arn, glue_version="4.0", worker_type="G.1X", number_of_workers=2, timeout=30, max_retries=0,
            command=glue.CfnJob.JobCommandProperty(name="glueetl", python_version="3", script_location=script.s3_object_url),
            connections=glue.CfnJob.ConnectionsListProperty(connections=[CONNECTION]),
            execution_property=glue.CfnJob.ExecutionPropertyProperty(max_concurrent_runs=4),
            default_arguments={"--extra-py-files": contracts.s3_object_url, "--CONNECTION_NAME": CONNECTION, "--SCHEMA": "esg", "--OUT_BUCKET": raw_bucket,
                               "--REPORT_BUCKET": out_bucket, "--job-language": "python", "--TempDir": f"s3://{raw_bucket}/tmp/glue/", "--enable-metrics": "false"})
        job.add_dependency(conn)

        # ── sync state machine ──────────────────────────────────────────────────────────────────
        sm_role = iam.Role(self, "SyncSfnRole", assumed_by=iam.ServicePrincipal("states.amazonaws.com"))
        sm_role.add_to_policy(iam.PolicyStatement(actions=["glue:StartJobRun", "glue:GetJobRun", "glue:GetJobRuns", "glue:BatchStopJobRun"],
                                                  resources=[f"arn:aws:glue:{region}:{acct}:job/{JOB}"]))
        sm_role.add_to_policy(iam.PolicyStatement(actions=["events:PutTargets", "events:PutRule", "events:DescribeRule"],
                                                  resources=[f"arn:aws:events:{region}:{acct}:rule/StepFunctionsGetEventsForGlueJobsRule"]))
        machine = sfn.CfnStateMachine(self, "SyncStateMachine", state_machine_name=SYNC_SM, role_arn=sm_role.role_arn,
                                      definition_string=(POC / "step_functions" / "esg_data_sync.asl.json").read_text())

        # ── Lambdas in the VPC ──────────────────────────────────────────────────────────────────
        layer_dir = POC / "build" / "pglayer"
        if not layer_dir.exists():
            raise RuntimeError("build/pglayer is missing. Run scripts/build_layer.sh (or the pip command in docs/DEPLOY_PLATFORM.md).")
        pg_layer = _lambda.LayerVersion(self, "PgLayer", code=_lambda.Code.from_asset(str(layer_dir)), compatible_runtimes=[_lambda.Runtime.PYTHON_3_12])
        common = dict(runtime=_lambda.Runtime.PYTHON_3_12, layers=[pg_layer], vpc=vpc, vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
                      security_groups=[tools_sg], log_retention=logs.RetentionDays.TWO_WEEKS, tracing=_lambda.Tracing.ACTIVE)
        env = {"DB_HOST": db.db_instance_endpoint_address, "DB_PORT": "5432", "DB_NAME": "esgdb"}

        def code(pkg: str) -> _lambda.Code:
            return _lambda.Code.from_asset(str(POC / "lambda"), ignore_mode=IgnoreMode.GIT, exclude=["/*", "!/_shared", f"!/{pkg}", "__pycache__", "*.pyc"])

        seed = _lambda.Function(self, "SeedFn", function_name="esg-rds-seed", handler="rds_seed.handler.lambda_handler", code=code("rds_seed"),
                                timeout=Duration.minutes(5), memory_size=512, description="Creates the source schema and loads the synthetic data",
                                environment={**env, "MASTER_SECRET_ARN": master_secret.secret_arn, "READER_SECRET_ARN": reader_secret.secret_arn, "SEED_BUCKET": raw_bucket}, **common)
        master_secret.grant_read(seed)
        reader_secret.grant_read(seed)
        seed.add_to_role_policy(iam.PolicyStatement(actions=["s3:GetObject"], resources=[f"arn:aws:s3:::{raw_bucket}/seed/rds/*"]))
        tools = _lambda.Function(self, "ToolsFn", function_name="esg-data-tools", handler="data_tools.handler.lambda_handler", code=code("data_tools"),
                                 timeout=Duration.seconds(30), memory_size=256, description="Read-only data tools for the AgentCore orchestrator",
                                 environment={**env, "READER_SECRET_ARN": reader_secret.secret_arn, "REPORT_BUCKET": out_bucket}, **common)
        reader_secret.grant_read(tools)
        tools.add_to_role_policy(iam.PolicyStatement(actions=["s3:GetObject"], resources=[f"arn:aws:s3:::{out_bucket}/etl-reports/*"]))

        CfnOutput(self, "SyncStateMachineArn", value=f"arn:aws:states:{region}:{acct}:stateMachine:{SYNC_SM}")
        CfnOutput(self, "ExtractJobName", value=JOB)
        CfnOutput(self, "SeedFunctionName", value=seed.function_name)
        CfnOutput(self, "DataToolsFunctionName", value=tools.function_name)
        machine.node.add_dependency(job)
