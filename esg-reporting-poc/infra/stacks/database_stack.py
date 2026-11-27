"""Source database: RDS PostgreSQL, encrypted, TLS required, private subnets only, 7-day backups, deletion protection."""

from __future__ import annotations

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack, Tags, aws_ec2 as ec2, aws_rds as rds, aws_secretsmanager as sm
from constructs import Construct


class EsgDatabaseStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, vpc: ec2.IVpc, db_sg: ec2.ISecurityGroup, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        Tags.of(self).add("Project", "ESG")
        self.db = rds.DatabaseInstance(
            self, "SourceDb", instance_identifier="esg-source-db", database_name="esgdb",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_16),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.SMALL),
            vpc=vpc, vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED), security_groups=[db_sg], publicly_accessible=False,
            credentials=rds.Credentials.from_generated_secret("esgadmin", secret_name="esg/rds/master"),
            allocated_storage=50, max_allocated_storage=200, storage_type=rds.StorageType.GP3, storage_encrypted=True,
            multi_az=False, backup_retention=Duration.days(7), copy_tags_to_snapshot=True, auto_minor_version_upgrade=True,
            deletion_protection=True, removal_policy=RemovalPolicy.SNAPSHOT)
        # Read-only user used by Glue and the agent's data tools. The seed Lambda creates the role with this password.
        self.reader_secret = sm.Secret(
            self, "ReaderSecret", secret_name="esg/rds/reader", description="Password of the read-only database user esg_reader",
            generate_secret_string=sm.SecretStringGenerator(secret_string_template='{"username":"esg_reader"}', generate_string_key="password",
                                                           password_length=32, exclude_punctuation=True))
        self.master_secret = self.db.secret
        CfnOutput(self, "DbEndpoint", value=self.db.db_instance_endpoint_address)
