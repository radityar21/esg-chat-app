"""Network for the source database and the jobs that read it. No NAT gateway and no internet route:
the isolated subnets reach S3 through a gateway endpoint and Secrets Manager through an interface endpoint."""

from __future__ import annotations

from aws_cdk import Stack, Tags, aws_ec2 as ec2
from constructs import Construct


class EsgNetworkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        Tags.of(self).add("Project", "ESG")
        self.vpc = ec2.Vpc(
            self, "Vpc", vpc_name="esg-vpc", ip_addresses=ec2.IpAddresses.cidr("10.40.0.0/16"), max_azs=2, nat_gateways=0,
            subnet_configuration=[ec2.SubnetConfiguration(name="isolated", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, cidr_mask=24)],
            gateway_endpoints={"S3": ec2.GatewayVpcEndpointOptions(service=ec2.GatewayVpcEndpointAwsService.S3)})

        self.glue_sg = ec2.SecurityGroup(self, "GlueSg", vpc=self.vpc, description="Glue jobs that read the source database", allow_all_outbound=True)
        self.glue_sg.add_ingress_rule(self.glue_sg, ec2.Port.all_tcp(), "Glue requires a self-referencing rule")
        self.tools_sg = ec2.SecurityGroup(self, "ToolsSg", vpc=self.vpc, description="Lambdas that read or seed the source database", allow_all_outbound=True)
        self.db_sg = ec2.SecurityGroup(self, "DbSg", vpc=self.vpc, description="Source database", allow_all_outbound=False)
        self.db_sg.add_ingress_rule(self.glue_sg, ec2.Port.tcp(5432), "Glue extract jobs")
        self.db_sg.add_ingress_rule(self.tools_sg, ec2.Port.tcp(5432), "Seed and data-tool Lambdas")

        endpoint_sg = ec2.SecurityGroup(self, "EndpointSg", vpc=self.vpc, description="Interface endpoints", allow_all_outbound=False)
        endpoint_sg.add_ingress_rule(self.tools_sg, ec2.Port.tcp(443))
        endpoint_sg.add_ingress_rule(self.glue_sg, ec2.Port.tcp(443))
        self.vpc.add_interface_endpoint("SecretsManager", service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER, security_groups=[endpoint_sg], private_dns_enabled=True)
