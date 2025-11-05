from aws_cdk import (
    Stack,
    Environment,
    aws_route53 as route53,
)
from constructs import Construct

class DnsStack(Stack):
    """
    Core stack for all resources common across applications and environments.
    Resources defined here may be one-off resources for a particular application and its environment,
    but any repeatable resources should be either extracted to a helper method or to a nested stack.
    """

    def __init__(self, scope: Construct, construct_id: str, *,
                 env: Environment, dns_zone_name: str) -> None:
        super().__init__(scope, construct_id, env=env)

        self.dns_zone_name = dns_zone_name

        self.hosted_zone = route53.PublicHostedZone(self, "HostedZone",
            zone_name=dns_zone_name
        )

        