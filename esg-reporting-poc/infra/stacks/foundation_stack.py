"""Foundation of the ESG reporting pipeline: storage, catalog, ETL, report generation and the Knowledge Base.

Everything the platform stack and the agent expect to exist, under the names the code uses:
    6 S3 buckets, Athena workgroup, 3 Glue databases (tables are created by scripts/apply_ddl.py)
    4 Glue ETL jobs (Scope 1, Scope 2, Scope 3 PCAF, aggregation)
    6 pipeline Lambdas + python-docx layer, report state machine, 2 SNS topics
    Bedrock Knowledge Base on S3 Vectors (no OpenSearch Serverless: no fixed monthly floor)
    the PII pseudonymisation secret
Deploy FIRST. Build artifacts with `python scripts/build_all.py` before `cdk deploy`.
"""

from __future__ import annotations

from pathlib import Path

from aws_cdk import (
    CfnOutput, Duration, RemovalPolicy, Stack, Tags,
    aws_athena as athena, aws_bedrock as bedrock, aws_glue as glue, aws_iam as iam, aws_lambda as _lambda, aws_logs as logs,
    aws_s3 as s3, aws_s3_assets as s3_assets, aws_s3vectors as s3vectors, aws_secretsmanager as sm, aws_sns as sns, aws_stepfunctions as sfn,
)
from constructs import Construct

POC = Path(__file__).resolve().parents[2]
BUILD = POC / "build"
KB_PREFIX = "documents/"  # the data source accepts ONE prefix; prompts/ and templates/ in the same bucket must not be indexed
EXPIRE_PREFIXES = ["agent-ledger/", "executions/", "platform-cache/", "etl-reports/"]  # operational data: 14 days
GLUE_JOBS = {  # job name -> script
    "esg-etl-scope1-direct": "glue_job_scope1_ghg.py", "esg-etl-scope2-indirect": "glue_job_scope2_electricity.py",
    "esg-etl-scope3-pcaf": "glue_job_scope3_pcaf.py", "esg-etl-aggregation": "glue_job_aggregation.py",
}
# name, folder, memory MB, timeout s
LAMBDAS = [("esg-validate-input", "validate_input", 256, 30), ("esg-athena-query", "athena_query", 512, 60), ("esg-section-gen", "section_gen", 1024, 240),
           ("esg-validation", "validation", 512, 60), ("esg-filter-sections", "filter_sections", 256, 30), ("esg-assembly-doc", "assembly_doc", 1024, 120)]


class EsgFoundationStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, routing_profile: str = "quality", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        Tags.of(self).add("Project", "ESG")
        acct, region = self.account, self.region
        for d in ("lambda-stage", "docxlayer", "agent.zip"):
            if not (BUILD / d).exists():
                raise RuntimeError(f"build/{d} is missing. Run: python scripts/build_all.py")

        # ── storage ─────────────────────────────────────────────────────────────────────────────
        def bucket(key: str, name: str, expire_days: int | None = None, prefixes: list[str] | None = None) -> s3.Bucket:
            rules = []
            if expire_days and not prefixes:
                rules.append(s3.LifecycleRule(id="expire", expiration=Duration.days(expire_days), abort_incomplete_multipart_upload_after=Duration.days(1)))
            for p in prefixes or []:
                rules.append(s3.LifecycleRule(id=f"expire-{p.strip('/')}", prefix=p, expiration=Duration.days(expire_days or 14), abort_incomplete_multipart_upload_after=Duration.days(1)))
            return s3.Bucket(self, key, bucket_name=f"{name}-{acct}", versioned=True, encryption=s3.BucketEncryption.S3_MANAGED, enforce_ssl=True,
                             block_public_access=s3.BlockPublicAccess.BLOCK_ALL, removal_policy=RemovalPolicy.RETAIN, lifecycle_rules=rules or None)

        raw = bucket("Raw", "esg-data-raw")
        curated = bucket("Curated", "esg-data-curated")
        aggregated = bucket("Aggregated", "esg-data-aggregated")
        output = bucket("Output", "esg-output-reports", 14, EXPIRE_PREFIXES)
        kb_docs = bucket("KbDocs", "esg-kb-documents")
        athena_results = bucket("AthenaResults", "esg-athena-results", 14)
        data_buckets = [raw, curated, aggregated, output, kb_docs, athena_results]
        b_arns = [b.bucket_arn for b in data_buckets] + [b.arn_for_objects("*") for b in data_buckets]

        athena.CfnWorkGroup(self, "Workgroup", name="esg-reporting-workgroup", description="ESG reporting queries", state="ENABLED", work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
            enforce_work_group_configuration=True, publish_cloud_watch_metrics_enabled=False,
            engine_version=athena.CfnWorkGroup.EngineVersionProperty(selected_engine_version="Athena engine version 3"),
            result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(output_location=f"s3://{athena_results.bucket_name}/query-results/")))

        pii_secret = sm.Secret(self, "PiiTokenSecret", secret_name="esg/pii-token-secret", description="HMAC key for PII pseudonyms. Do not rotate casually: tokens would change.",
                               generate_secret_string=sm.SecretStringGenerator(password_length=48, exclude_punctuation=True))

        # ── Glue ETL ────────────────────────────────────────────────────────────────────────────
        glue_role = iam.Role(self, "GlueRole", role_name="ESGGlueRole", assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
                             managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole")])
        for b in (raw, curated, aggregated):
            b.grant_read_write(glue_role)
        for job, script_name in GLUE_JOBS.items():
            script = s3_assets.Asset(self, f"Script{job}", path=str(POC / "glue_jobs" / script_name))
            script.grant_read(glue_role)
            glue.CfnJob(self, f"Job{job}", name=job, role=glue_role.role_arn, glue_version="4.0", worker_type="G.1X", number_of_workers=2, timeout=60, max_retries=0,
                        command=glue.CfnJob.JobCommandProperty(name="glueetl", python_version="3", script_location=script.s3_object_url),
                        execution_property=glue.CfnJob.ExecutionPropertyProperty(max_concurrent_runs=2),
                        default_arguments={"--enable-glue-datacatalog": "true", "--job-language": "python", "--TempDir": f"s3://{raw.bucket_name}/tmp/glue/"})

        # ── Lambdas ─────────────────────────────────────────────────────────────────────────────
        model_arns = [f"arn:aws:bedrock:{region}:{acct}:inference-profile/us.anthropic.claude-*-4-5-*", "arn:aws:bedrock:*::foundation-model/anthropic.claude-*-4-5-*"]
        kb_bucket_arn = kb_docs.bucket_arn
        lambda_role = iam.Role(self, "LambdaRole", role_name="ESGLambdaRole", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                               managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")])
        lambda_role.add_to_policy(iam.PolicyStatement(actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:GetBucketLocation", "s3:AbortMultipartUpload"], resources=b_arns))
        lambda_role.add_to_policy(iam.PolicyStatement(actions=["athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults", "athena:StopQueryExecution", "athena:GetWorkGroup"],
                                                      resources=[f"arn:aws:athena:{region}:{acct}:workgroup/esg-reporting-workgroup"]))
        lambda_role.add_to_policy(iam.PolicyStatement(actions=["glue:GetTable", "glue:GetTables", "glue:GetDatabase", "glue:GetDatabases", "glue:GetPartitions"],
                                                      resources=[f"arn:aws:glue:{region}:{acct}:catalog", f"arn:aws:glue:{region}:{acct}:database/esg_*", f"arn:aws:glue:{region}:{acct}:table/esg_*/*"]))
        lambda_role.add_to_policy(iam.PolicyStatement(actions=["bedrock:InvokeModel"], resources=model_arns))
        lambda_role.add_to_policy(iam.PolicyStatement(actions=["dynamodb:PutItem"], resources=[f"arn:aws:dynamodb:{region}:{acct}:table/esg-llm-usage"]))  # table is created by the platform stack
        pii_secret.grant_read(lambda_role)

        docx_layer = _lambda.LayerVersion(self, "DocxLayer", layer_version_name="esg-python-docx", code=_lambda.Code.from_asset(str(BUILD / "docxlayer")),
                                          compatible_runtimes=[_lambda.Runtime.PYTHON_3_12], compatible_architectures=[_lambda.Architecture.X86_64])
        fns: dict[str, _lambda.Function] = {}
        for name, folder, mem, timeout in LAMBDAS:
            env = {}
            if folder == "section_gen":
                env = {"USAGE_TABLE": "esg-llm-usage", "MODEL_ROUTING_PROFILE": routing_profile, "USAGE_TTL_DAYS": "14",
                       "PII_TOKEN_SECRET_ARN": pii_secret.secret_name, "PII_REQUIRE_SECRET": "1"}
            if folder == "validation":
                env = {"VALIDATOR_CALIBRATION": "on"}
            fns[name] = _lambda.Function(self, f"Fn{folder}", function_name=name, runtime=_lambda.Runtime.PYTHON_3_12, architecture=_lambda.Architecture.X86_64,
                                         handler="handler.lambda_handler", code=_lambda.Code.from_asset(str(BUILD / "lambda-stage" / folder)), role=lambda_role,
                                         memory_size=mem, timeout=Duration.seconds(timeout), environment=env or None, log_retention=logs.RetentionDays.TWO_WEEKS,
                                         layers=[docx_layer] if folder == "assembly_doc" else None, tracing=_lambda.Tracing.ACTIVE)

        # ── Knowledge Base on S3 Vectors ────────────────────────────────────────────────────────
        vbucket = s3vectors.CfnVectorBucket(self, "VectorBucket", vector_bucket_name=f"esg-kb-vectors-{acct}")
        vindex = s3vectors.CfnIndex(self, "VectorIndex", vector_bucket_arn=vbucket.attr_vector_bucket_arn, index_name="esg-kb-index", data_type="float32", dimension=1024,
                                    distance_metric="cosine", metadata_configuration=s3vectors.CfnIndex.MetadataConfigurationProperty(
                                        non_filterable_metadata_keys=["AMAZON_BEDROCK_TEXT", "AMAZON_BEDROCK_METADATA"]))
        vindex.add_dependency(vbucket)
        embed_arn = f"arn:aws:bedrock:{region}::foundation-model/amazon.titan-embed-text-v2:0"
        kb_role = iam.Role(self, "KbRole", assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com", conditions={
            "StringEquals": {"aws:SourceAccount": acct}, "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock:{region}:{acct}:knowledge-base/*"}}))
        kb_policy = iam.Policy(self, "KbPolicy", statements=[
            iam.PolicyStatement(actions=["bedrock:InvokeModel"], resources=[embed_arn]),
            iam.PolicyStatement(actions=["s3:GetObject", "s3:ListBucket"], resources=[kb_bucket_arn, f"{kb_bucket_arn}/*"], conditions={"StringEquals": {"aws:ResourceAccount": acct}}),
            iam.PolicyStatement(actions=["s3vectors:GetIndex", "s3vectors:QueryVectors", "s3vectors:PutVectors", "s3vectors:GetVectors", "s3vectors:DeleteVectors", "s3vectors:ListVectors"],
                                resources=[vindex.attr_index_arn])])
        kb_policy.attach_to_role(kb_role)
        kb = bedrock.CfnKnowledgeBase(
            self, "KnowledgeBase", name="ESG-Framework-KB", description="ESG frameworks and reference reports for report generation (RAG)", role_arn=kb_role.role_arn,
            knowledge_base_configuration=bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(type="VECTOR", vector_knowledge_base_configuration=bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                embedding_model_arn=embed_arn, embedding_model_configuration=bedrock.CfnKnowledgeBase.EmbeddingModelConfigurationProperty(
                    bedrock_embedding_model_configuration=bedrock.CfnKnowledgeBase.BedrockEmbeddingModelConfigurationProperty(dimensions=1024, embedding_data_type="FLOAT32")))),
            storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(type="S3_VECTORS", s3_vectors_configuration=bedrock.CfnKnowledgeBase.S3VectorsConfigurationProperty(index_arn=vindex.attr_index_arn)))
        kb.node.add_dependency(kb_policy)
        kb.node.add_dependency(vindex)
        data_source = bedrock.CfnDataSource(
            self, "KbDataSource", name="esg-framework-documents", knowledge_base_id=kb.attr_knowledge_base_id, data_deletion_policy="RETAIN",
            data_source_configuration=bedrock.CfnDataSource.DataSourceConfigurationProperty(type="S3", s3_configuration=bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                bucket_arn=kb_bucket_arn, inclusion_prefixes=[KB_PREFIX])),
            vector_ingestion_configuration=bedrock.CfnDataSource.VectorIngestionConfigurationProperty(chunking_configuration=bedrock.CfnDataSource.ChunkingConfigurationProperty(
                chunking_strategy="SEMANTIC", semantic_chunking_configuration=bedrock.CfnDataSource.SemanticChunkingConfigurationProperty(
                    max_tokens=700, buffer_size=1, breakpoint_percentile_threshold=90))))
        lambda_role.add_to_policy(iam.PolicyStatement(actions=["bedrock:Retrieve"], resources=[kb.attr_knowledge_base_arn]))
        self.kb_id = kb.attr_knowledge_base_id

        # ── report state machine ────────────────────────────────────────────────────────────────
        topics = [sns.Topic(self, "HumanReview", topic_name="ESG-HumanReview"), sns.Topic(self, "ReportComplete", topic_name="ESG-ReportComplete")]
        sfn_role = iam.Role(self, "SfnRole", role_name="ESGStepFunctionsRole", assumed_by=iam.ServicePrincipal("states.amazonaws.com"))
        sfn_role.add_to_policy(iam.PolicyStatement(actions=["lambda:InvokeFunction"], resources=[f.function_arn for f in fns.values()] + [f"{f.function_arn}:*" for f in fns.values()]))
        sfn_role.add_to_policy(iam.PolicyStatement(actions=["glue:StartJobRun", "glue:GetJobRun", "glue:GetJobRuns", "glue:BatchStopJobRun"],
                                                   resources=[f"arn:aws:glue:{region}:{acct}:job/{j}" for j in GLUE_JOBS]))
        sfn_role.add_to_policy(iam.PolicyStatement(actions=["sns:Publish"], resources=[t.topic_arn for t in topics]))
        sfn_role.add_to_policy(iam.PolicyStatement(actions=["events:PutTargets", "events:PutRule", "events:DescribeRule"],
                                                   resources=[f"arn:aws:events:{region}:{acct}:rule/StepFunctionsGetEventsForGlueJobsRule"]))
        machine = sfn.CfnStateMachine(self, "ReportStateMachine", state_machine_name="ESGReportGenerationStateMachine", role_arn=sfn_role.role_arn,
                                      definition_string=(POC / "step_functions" / "esg_orchestrator.asl.json").read_text())
        for f in fns.values():
            machine.node.add_dependency(f)

        CfnOutput(self, "KnowledgeBaseId", value=kb.attr_knowledge_base_id, description="KB id (also exported to the platform stack automatically)")
        CfnOutput(self, "KnowledgeBaseDataSourceId", value=data_source.attr_data_source_id)
        CfnOutput(self, "KbBucket", value=kb_docs.bucket_name)
        CfnOutput(self, "ReportStateMachineArn", value=f"arn:aws:states:{region}:{acct}:stateMachine:ESGReportGenerationStateMachine")
