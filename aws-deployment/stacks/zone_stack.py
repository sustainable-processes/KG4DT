from aws_cdk import (
    NestedStack,
    Duration,
    Stack,
    RemovalPolicy,
    CfnOutput,
    Environment,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_autoscaling as autoscaling,
    aws_cognito as cognito,
    aws_secretsmanager as secretsmanager
)
from constructs import Construct

class ZoneStack(Stack):
    """
    Reusable subnets selection construct for private subnets in zone's VPC
    that are intended for hosting application components.
    """
    APPLICATION_SUBNETS = ec2.SubnetSelection(subnet_group_name="Application")

    """
    Zone CloudFormation stack defines resources used by a related group of application environments.
    Typical zones are production, staging, non-production.
    This stack manages the following types of resources:
    * VPC and subnets shared by all environments
    * Bastion host for the zone
    * ECS cluster used by containerised workloads in all environments
    """
    def __init__(self, scope: Construct, *, env: Environment,
            zone_name: str, vpc_cidr: str,
            az_count: int, ngw_count: int) -> None:
        super().__init__(scope, zone_name + "Zone", env=env)

        self.zone_name = zone_name

        # Note: using only one NAT gateway is less resilient, but cheaper and allows to keep within the IP address limit
        # TODO remove the restriction when fully in production
        self.vpc = ec2.Vpc(self, "VPC",
            ip_addresses=ec2.IpAddresses.cidr(vpc_cidr),
            max_azs=az_count,
            nat_gateways=ngw_count,
            subnet_configuration=[ec2.SubnetConfiguration(
                subnet_type=ec2.SubnetType.PUBLIC,
                name="Public",
                cidr_mask=20
            ), ec2.SubnetConfiguration(
                cidr_mask=20,
                name="Application",
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ), ec2.SubnetConfiguration(
                cidr_mask=20,
                name="Database",
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            )
        ])

        # Bastion host is created in the application subnet, and it accesses external resources via a NAT gateway
        # Use AWS Session Manager for logging into the bastion host
        ec2.BastionHostLinux(self, "Bastion",
            vpc=self.vpc,
            instance_name=zone_name + "Bastion",
            subnet_selection=ec2.SubnetSelection(subnet_group_name="Application")
        )

        # use private route for accessing S3 buckets in the region to avoid NAT charges
        ec2.GatewayVpcEndpoint(self, "S3GatewayEndpoint",
            vpc=self.vpc,
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )

        # use private route to access ECR for pulling container images
        ec2.InterfaceVpcEndpoint(self, "EcrInterfaceEndpoint",
            vpc=self.vpc,
            service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
            private_dns_enabled=True,
            subnets=ZoneStack.APPLICATION_SUBNETS,
        )