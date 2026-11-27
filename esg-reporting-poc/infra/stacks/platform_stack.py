"""ESG Intelligence Platform stack.

Creates (everything NEW; the existing report pipeline, Glue jobs, buckets and Lambdas are referenced by name):
    - DynamoDB usage table (token FinOps)
    - esg-platform-api Lambda + HTTP API (+ Function URL for long agent chats)
    - esg-agent-trigger Lambda + EventBridge rule (report state machine finished -> AgentCore supervise)
    - daily regulatory scan schedule
    - GHG inventory state machine (from step_functions/esg_ghg_inventory.asl.json)
    - AgentCore Runtime (container built from agentcore/Dockerfile, ARM64) with its execution role
    - IAM managed policy to attach to the EXISTING pipeline Lambda roles so they can write usage metering

Deploy:  cdk deploy EsgPlatformStack -c apiKey=<long random string>   (see docs/DEPLOY_PLATFORM.md)
"""

from __future__ import annotations

from pathlib import Path

from aws_cdk import (
    CfnOutput, Duration, IgnoreMode, RemovalPolicy, Stack, Tags,
    aws_apigatewayv2 as apigw,
    aws_bedrockagentcore as agentcore,
    aws_dynamodb as ddb,
    aws_ecr_assets as ecr_assets,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_stepfunctions as sfn,
)
from aws_cdk.aws_apigatewayv2_integrations import HttpLambdaIntegration
from constructs import Construct

POC = Path(__file__).resolve().parents[2]  # esg-reporting-poc/

PLATFORM_FN_NAME = "esg-platform-api"
TRIGGER_FN_NAME = "esg-agent-trigger"
GHG_SM_NAME = "ESGGhgInventoryStateMachine"
REPORT_SM_NAME = "ESGReportGenerationStateMachine"
GLUE_JOBS = ["esg-etl-scope1-direct", "esg-etl-scope2-indirect", "esg-etl-scope3-pcaf", "esg-etl-aggregation"]
PIPELINE_LAMBDAS = ["esg-validate-input", "esg-athena-query", "esg-section-gen", "esg-validation", "esg-filter-sections", "esg-assembly-doc"]
DATA_BUCKETS = ["esg-data-raw", "esg-data-curated", "esg-data-aggregated", "esg-output-reports", "esg-kb-documents"]
# Files that must not reach the container build context (keeps the asset small and the hash stable)
IMAGE_EXCLUDE = ["data", "result", "docs", "infra", "cdk.out", "tests", "glue_jobs", "sql", "step_functions", "templates", "prompts",
                 "benchmark_advisory", "scripts", "**/__pycache__", "**/*.pyc", ".git", "*.md", "build", ".pytest_cache", "agent", "config",
                 "lambda/section_gen", "lambda/validation", "lambda/athena_query", "lambda/assembly_doc", "lambda/filter_sections", "lambda/validate_input",
                 "lambda/dashboard_data", "lambda/history", "lambda/review_handler", "lambda/status_check", "lambda/platform_api", "lambda/agent_trigger"]


class EsgPlatformStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, api_key: str, allowed_origin: str = "*",
                 company_name: str = "Bank Nusantara Sejahtera", routing_profile: str = "quality", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        acct, region = self.account, self.region
        output_bucket = f"esg-output-reports-{acct}"
        report_sm_arn = f"arn:aws:states:{region}:{acct}:stateMachine:{REPORT_SM_NAME}"
        ghg_sm_arn = f"arn:aws:states:{region}:{acct}:stateMachine:{GHG_SM_NAME}"
        platform_fn_arn = f"arn:aws:lambda:{region}:{acct}:function:{PLATFORM_FN_NAME}"
        bucket_arns = [f"arn:aws:s3:::{b}-{acct}" for b in DATA_BUCKETS]
        bucket_objs = [a + "/*" for a in bucket_arns]
        Tags.of(self).add("Project", "ESG")

        # ── usage table ────────────────────────────────────────────────────────────────────────────
        usage = ddb.Table(self, "UsageTable", table_name="esg-llm-usage", partition_key=ddb.Attribute(name="day", type=ddb.AttributeType.STRING),
                          sort_key=ddb.Attribute(name="sk", type=ddb.AttributeType.STRING), billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
                          point_in_time_recovery=True, removal_policy=RemovalPolicy.RETAIN, time_to_live_attribute="ttl")

        meter_policy = iam.ManagedPolicy(self, "UsageMeterWritePolicy", managed_policy_name="esg-usage-meter-write",
                                         description="Attach to the existing pipeline Lambda roles so section_gen can write token usage.",
                                         statements=[iam.PolicyStatement(actions=["dynamodb:PutItem"], resources=[usage.table_arn])])

        # ── platform API Lambda ────────────────────────────────────────────────────────────────────
        layer_dir = POC / "build" / "layer"
        layers = [_lambda.LayerVersion(self, "Boto3Layer", code=_lambda.Code.from_asset(str(layer_dir)), compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
                                       description="Recent boto3 (bedrock-agentcore client). Built by scripts/build_layer.sh")] if layer_dir.exists() else []
        if not layers:
            raise RuntimeError("build/layer is missing. Run: bash scripts/build_layer.sh (the Lambda runtime's boto3 may not include bedrock-agentcore).")

        env = {
            "OUTPUT_BUCKET": output_bucket, "BANK_ID": "GENERIC_FI_001", "COMPANY_NAME": company_name, "BASE_YEAR": "2023", "AWS_ACCOUNT_ID": acct,
            "USAGE_TABLE": usage.table_name, "MODEL_ROUTING_PROFILE": routing_profile, "ALLOWED_ORIGIN": allowed_origin, "API_KEY": api_key,
            "ATHENA_WORKGROUP": "esg-reporting-workgroup",
        }
        platform_fn = _lambda.Function(
            self, "PlatformFn", function_name=PLATFORM_FN_NAME, runtime=_lambda.Runtime.PYTHON_3_12, handler="platform_api.handler.lambda_handler",
            code=_lambda.Code.from_asset(str(POC / "lambda"), ignore_mode=IgnoreMode.GIT,
                                         exclude=["/*", "!/_shared", "!/platform_api", "__pycache__", "*.pyc"]),
            timeout=Duration.seconds(300), memory_size=512, environment=env, layers=layers, log_retention=logs.RetentionDays.ONE_MONTH,
            description="ESG platform API: compliance, GHG inventory, portfolio, scenarios, governance, FinOps")
        usage.grant_read_write_data(platform_fn)
        platform_fn.add_to_role_policy(iam.PolicyStatement(actions=["athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults", "athena:StopQueryExecution"],
                                                           resources=[f"arn:aws:athena:{region}:{acct}:workgroup/esg-reporting-workgroup"]))
        platform_fn.add_to_role_policy(iam.PolicyStatement(actions=["glue:GetTable", "glue:GetTables", "glue:GetDatabase", "glue:GetPartitions"],
                                                           resources=[f"arn:aws:glue:{region}:{acct}:catalog", f"arn:aws:glue:{region}:{acct}:database/esg_*",
                                                                      f"arn:aws:glue:{region}:{acct}:table/esg_*/*"]))
        platform_fn.add_to_role_policy(iam.PolicyStatement(actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:GetBucketLocation", "s3:AbortMultipartUpload"],
                                                           resources=bucket_arns + bucket_objs))
        platform_fn.add_to_role_policy(iam.PolicyStatement(actions=["bedrock:InvokeModel", "bedrock:Converse", "bedrock:ApplyGuardrail"], resources=["*"]))
        platform_fn.add_to_role_policy(iam.PolicyStatement(actions=["bedrock-agentcore:InvokeAgentRuntime"], resources=[f"arn:aws:bedrock-agentcore:{region}:{acct}:runtime/*"]))

        http_api = apigw.HttpApi(self, "PlatformApi", api_name="esg-platform-api",
                                 cors_preflight=apigw.CorsPreflightOptions(allow_origins=[allowed_origin], allow_methods=[apigw.CorsHttpMethod.GET, apigw.CorsHttpMethod.POST, apigw.CorsHttpMethod.OPTIONS],
                                                                           allow_headers=["Content-Type", "x-api-key"], max_age=Duration.hours(1)))
        integ = HttpLambdaIntegration("PlatformIntegration", platform_fn)
        http_api.add_routes(path="/{proxy+}", methods=[apigw.HttpMethod.ANY], integration=integ)
        http_api.add_routes(path="/health", methods=[apigw.HttpMethod.GET], integration=integ)

        # Function URL: API Gateway cuts requests at 30 s; an agent chat turn can take longer. Protected by the same x-api-key check.
        fn_url = platform_fn.add_function_url(auth_type=_lambda.FunctionUrlAuthType.NONE, invoke_mode=_lambda.InvokeMode.BUFFERED,
                                              cors=_lambda.FunctionUrlCorsOptions(allowed_origins=[allowed_origin], allowed_methods=[_lambda.HttpMethod.GET, _lambda.HttpMethod.POST],
                                                                                  allowed_headers=["content-type", "x-api-key"]))

        # ── GHG inventory state machine ────────────────────────────────────────────────────────────
        ghg_role = iam.Role(self, "GhgSfnRole", assumed_by=iam.ServicePrincipal("states.amazonaws.com"))
        ghg_role.add_to_policy(iam.PolicyStatement(actions=["glue:StartJobRun", "glue:GetJobRun", "glue:GetJobRuns", "glue:BatchStopJobRun"],
                                                   resources=[f"arn:aws:glue:{region}:{acct}:job/{j}" for j in GLUE_JOBS]))
        ghg_role.add_to_policy(iam.PolicyStatement(actions=["lambda:InvokeFunction"], resources=[platform_fn_arn, platform_fn_arn + ":*"]))
        ghg_role.add_to_policy(iam.PolicyStatement(actions=["events:PutTargets", "events:PutRule", "events:DescribeRule"],
                                                   resources=[f"arn:aws:events:{region}:{acct}:rule/StepFunctionsGetEventsForGlueJobsRule"]))
        asl = (POC / "step_functions" / "esg_ghg_inventory.asl.json").read_text()
        sfn.CfnStateMachine(self, "GhgStateMachine", state_machine_name=GHG_SM_NAME, role_arn=ghg_role.role_arn, definition_string=asl,
                            definition_substitutions={"PlatformFnArn": platform_fn_arn})

        # ── AgentCore Runtime ──────────────────────────────────────────────────────────────────────
        image = ecr_assets.DockerImageAsset(self, "OrchestratorImage", directory=str(POC), file="agentcore/Dockerfile",
                                            platform=ecr_assets.Platform.LINUX_ARM64, exclude=IMAGE_EXCLUDE)
        rt_role = iam.Role(self, "RuntimeRole", assumed_by=iam.ServicePrincipal(
            "bedrock-agentcore.amazonaws.com", conditions={"StringEquals": {"aws:SourceAccount": acct}, "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{acct}:*"}}))
        image.repository.grant_pull(rt_role)
        rt_role.add_to_policy(iam.PolicyStatement(actions=["ecr:GetAuthorizationToken"], resources=["*"]))
        rt_role.add_to_policy(iam.PolicyStatement(actions=["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogStreams", "logs:DescribeLogGroups"],
                                                  resources=[f"arn:aws:logs:{region}:{acct}:log-group:/aws/bedrock-agentcore/runtimes/*", f"arn:aws:logs:{region}:{acct}:log-group:*"]))
        rt_role.add_to_policy(iam.PolicyStatement(actions=["xray:PutTraceSegments", "xray:PutTelemetryRecords", "xray:GetSamplingRules", "xray:GetSamplingTargets", "cloudwatch:PutMetricData"], resources=["*"]))
        rt_role.add_to_policy(iam.PolicyStatement(actions=["bedrock-agentcore:GetWorkloadAccessToken", "bedrock-agentcore:GetWorkloadAccessTokenForJWT", "bedrock-agentcore:GetWorkloadAccessTokenForUserId"],
                                                  resources=[f"arn:aws:bedrock-agentcore:{region}:{acct}:workload-identity-directory/default", f"arn:aws:bedrock-agentcore:{region}:{acct}:workload-identity-directory/default/workload-identity/*"]))
        rt_role.add_to_policy(iam.PolicyStatement(actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream", "bedrock:Converse", "bedrock:ConverseStream"], resources=["*"]))
        rt_role.add_to_policy(iam.PolicyStatement(actions=["states:StartExecution", "states:DescribeExecution", "states:GetExecutionHistory", "states:StopExecution"],
                                                  resources=[report_sm_arn, ghg_sm_arn, f"arn:aws:states:{region}:{acct}:execution:{REPORT_SM_NAME}:*", f"arn:aws:states:{region}:{acct}:execution:{GHG_SM_NAME}:*"]))
        fn_arns = [f"arn:aws:lambda:{region}:{acct}:function:{n}" for n in PIPELINE_LAMBDAS + [PLATFORM_FN_NAME]]
        rt_role.add_to_policy(iam.PolicyStatement(actions=["lambda:InvokeFunction"], resources=fn_arns))
        rt_role.add_to_policy(iam.PolicyStatement(actions=["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"], resources=bucket_arns + bucket_objs))
        rt_role.add_to_policy(iam.PolicyStatement(actions=["bedrock:Retrieve"], resources=[f"arn:aws:bedrock:{region}:{acct}:knowledge-base/*"]))

        runtime = agentcore.CfnRuntime(
            self, "OrchestratorRuntime", agent_runtime_name="esg_orchestrator", description="ESG report orchestrator: routes requests, supervises Step Functions, self-corrects validation failures",
            role_arn=rt_role.role_arn, agent_runtime_artifact=agentcore.CfnRuntime.AgentRuntimeArtifactProperty(
                container_configuration=agentcore.CfnRuntime.ContainerConfigurationProperty(container_uri=image.image_uri)),
            network_configuration=agentcore.CfnRuntime.NetworkConfigurationProperty(network_mode="PUBLIC"),
            environment_variables={
                "AWS_REGION": region, "AWS_ACCOUNT_ID": acct, "REPORT_STATE_MACHINE_ARN": report_sm_arn, "GHG_STATE_MACHINE_ARN": ghg_sm_arn,
                "OUTPUT_BUCKET": output_bucket, "PLATFORM_FUNCTION": PLATFORM_FN_NAME, "KB_ID": "WVREXI1LEI", "BANK_ID": "GENERIC_FI_001",
                "MAX_CORRECTION_ATTEMPTS": "2", "MAX_PIPELINE_RESTARTS": "1", "MODEL_ROUTING_PROFILE": routing_profile, "USAGE_TABLE": usage.table_name,
                "VALIDATOR_CALIBRATION": "on"})
        rt_role.add_to_policy(iam.PolicyStatement(actions=["dynamodb:PutItem"], resources=[usage.table_arn]))
        runtime.node.add_dependency(rt_role)

        # ── wire the Lambda to the runtime (done with an escape hatch to avoid a circular reference) ──
        platform_fn.add_environment("AGENTCORE_RUNTIME_ARN", runtime.attr_agent_runtime_arn)

        # ── agent trigger ──────────────────────────────────────────────────────────────────────────
        trigger = _lambda.Function(
            self, "TriggerFn", function_name=TRIGGER_FN_NAME, runtime=_lambda.Runtime.PYTHON_3_12, handler="handler.lambda_handler",
            code=_lambda.Code.from_asset(str(POC / "lambda" / "agent_trigger")), timeout=Duration.seconds(60), memory_size=256, layers=layers,
            environment={"AGENTCORE_RUNTIME_ARN": runtime.attr_agent_runtime_arn, "REPORT_STATE_MACHINE_ARN": report_sm_arn}, log_retention=logs.RetentionDays.ONE_MONTH)
        trigger.add_to_role_policy(iam.PolicyStatement(actions=["bedrock-agentcore:InvokeAgentRuntime"], resources=[f"arn:aws:bedrock-agentcore:{region}:{acct}:runtime/*"]))
        events.Rule(self, "ReportFinished", description="Report pipeline reached a terminal state: hand over to the AgentCore orchestrator",
                    event_pattern=events.EventPattern(source=["aws.states"], detail_type=["Step Functions Execution Status Change"],
                                                      detail={"stateMachineArn": [report_sm_arn], "status": ["SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"]}),
                    targets=[targets.LambdaFunction(trigger, retry_attempts=2)])
        events.Rule(self, "RegulatoryScan", description="Daily regulatory change scan", schedule=events.Schedule.cron(minute="0", hour="1"),
                    targets=[targets.LambdaFunction(platform_fn, retry_attempts=1)])

        CfnOutput(self, "PlatformApiUrl", value=http_api.api_endpoint, description="VITE_PLATFORM_API_URL")
        CfnOutput(self, "PlatformFunctionUrl", value=fn_url.url, description="VITE_AGENT_CHAT_URL (long-running chat turns)")
        CfnOutput(self, "AgentRuntimeArn", value=runtime.attr_agent_runtime_arn)
        CfnOutput(self, "GhgStateMachineArn", value=ghg_sm_arn)
        CfnOutput(self, "UsageTableName", value=usage.table_name)
        CfnOutput(self, "UsageMeterPolicyArn", value=meter_policy.managed_policy_arn, description="Attach to the existing pipeline Lambda roles")
