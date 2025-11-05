from aws_cdk import (
    Stack,
    Environment,
    aws_certificatemanager as acm,
    aws_route53 as route53
)
from constructs import Construct

class CertStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *,
                 env: Environment, dns_zone_name: str) -> None:
        super().__init__(scope, construct_id, env=env, cross_region_references=True)

        hosted_zone = route53.HostedZone.from_lookup(self, "DNSZone", domain_name=dns_zone_name)

        self.web_cert = acm.Certificate(self, "WorkbenchWebUICert",
            domain_name="kg4dt.kg.cdi-sg.com",
            validation=acm.CertificateValidation.from_dns(hosted_zone)
        )