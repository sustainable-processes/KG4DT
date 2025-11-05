from aws_cdk import (
    NestedStack,
    Duration,
    Stack,
    RemovalPolicy,
    CfnOutput,
    Environment,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
    aws_certificatemanager as acm,
    aws_ec2 as ec2,
    aws_autoscaling as autoscaling,
    aws_ecs as ecs,
    aws_logs as logs,
    aws_ecs_patterns as ecs_patterns,
    aws_cognito as cognito,
    aws_rds as rds,
    aws_elasticloadbalancingv2 as elb,
    aws_elasticloadbalancingv2_targets as elb_targets
)
from constructs import Construct

from stacks.dns_stack import DnsStack
from stacks.cert_stack import CertStack

class UserPoolStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *,
                 env: Environment,
                 user_pool_name: str, user_pool_domain_prefix: str,
                 dns_zone_name: str, auth_subdomain: str) -> None:
        super().__init__(scope, construct_id, env=env, cross_region_references=True)

        self.user_pool = cognito.UserPool(self, "UserPool",
            user_pool_name=user_pool_name,
            self_sign_up_enabled=True, # Changed - allow users to sign up
            sign_in_aliases=cognito.SignInAliases(
                username=False,  
                phone=False,
                email=True
            ),
            auto_verify=cognito.AutoVerifiedAttrs(email=True, phone=False),
            password_policy=cognito.PasswordPolicy(min_length=8, require_symbols=True), # added
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=False),
                fullname=cognito.StandardAttribute(required=True, mutable=True)
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY
        )

        # see comment in WorkbenchStack, this is a workaround for CDK issue
        CfnOutput(self, "UserPoolId",
            value=self.user_pool.user_pool_id,
            export_name="userPoolId"
        )
        CfnOutput(self, "UserPoolProviderUrl",
            value=self.user_pool.user_pool_provider_url,
            export_name="userPoolProviderUrl"
        )

        # # custom domain for Cognito screens
        # hosted_zone = route53.HostedZone.from_lookup(self, "DNSZone", domain_name=dns_zone_name)

        # #auth_subdomain = "authkg"
        # auth_domain_name = auth_subdomain + "." + dns_zone_name

        # custom_domain = self.user_pool.add_domain("CustomAuthDomain",
        #     custom_domain=cognito.CustomDomainOptions(
        #         domain_name=auth_domain_name,
        #         certificate=cert_stack.auth_domain_cert
        #     )
        # )

        # # DNS record for the auth domain
        # route53.CnameRecord(self, "AuthCnameRecord",
        #     zone=hosted_zone,
        #     record_name=auth_subdomain,
        #     domain_name=custom_domain.cloud_front_domain_name
        # )

        self.user_pool_domain = self.user_pool.add_domain("UserPoolDomain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=user_pool_domain_prefix  # e.g., "kg4dt"
            )
        )

        CfnOutput(self, "UserPoolDomainUrl",
            value=f"{user_pool_domain_prefix}.auth.{self.region}.amazoncognito.com",
            export_name="userPoolDomain"
        )