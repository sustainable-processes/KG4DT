#!/usr/bin/env python3
import aws_cdk as cdk

from stacks.workbench_stack import WorkbenchStack
from stacks.knowledge_graph_stack import KnowledgeGraphStack 
from stacks.zone_stack import ZoneStack
from stacks.dns_stack import DnsStack
from stacks.cert_stack import CertStack
from stacks.user_pool_stack import UserPoolStack
from stacks.workbench_app_stack import WorkbenchAppStack
from stacks.cluster_stack import ClusterStack

env = cdk.Environment(account='124355682815', region='ap-southeast-1')

# Create CDK App
app = cdk.App()

# DNS Stack
dns_stack = DnsStack(app, "DNSZone", env=env, dns_zone_name="kg.cdi-sg.com")

# Cognito User Pool Stack
user_pool_stack = UserPoolStack(app, "Users",
    env=env,
    user_pool_name="users",
    user_pool_domain_prefix="kg4dt",
    dns_zone_name=dns_stack.dns_zone_name,
    auth_subdomain="auth"
)

# Define Networking (VPCs, NAT, etc.)
prod_zone = ZoneStack(app,
    env=env,
    zone_name="Prod",
    vpc_cidr="10.0.0.0/16",
    az_count=2,
    ngw_count=2,
)

# non_prod_zone = ZoneStack(app,
#     env=env,
#     zone_name="NonProd",
#     vpc_cidr="10.64.0.0/16",
#     az_count=2,
#     ngw_count=2,
# )

cert_stack = CertStack(app, "AcmCertificates",
    env=env,
    dns_zone_name=dns_stack.dns_zone_name
)

ecs_prod_zone = ClusterStack(app, "ClusterStackProd", env=env, env_name="Prod", zone_stack=prod_zone, cert_stack=cert_stack)

# Workbench ECR Repo & App Stack
hoster_workbench = WorkbenchAppStack(app, "WorkbenchAppStack", env=env)

# Deploy Knowledge Graph Stack (Production)
knowledge_graph_stack = KnowledgeGraphStack(app,
    env=env,
    env_name="Prod",
    zone_stack=prod_zone,
    cluster = ecs_prod_zone,
    image_tag="prod",
    app_stack=hoster_workbench

)


# # Deploy Workbench Stack (Production)
workbench_stack = WorkbenchStack(app,
    env=env,
    env_name="Prod",
    zone_stack=prod_zone,
    cluster_stack = ecs_prod_zone,
    dns_zone_name=dns_stack.dns_zone_name,
    hosted_zone=dns_stack.hosted_zone,  # Pass the hosted_zone directly
    image_tag="prod",
    webui_domain_name_prefix="kg4dt",
    app_stack=hoster_workbench,
    kg_stack=knowledge_graph_stack,  # Pass ALB DNS name
    cert_stack=cert_stack,
    shared_alb=ecs_prod_zone.shared_alb,
    shared_alb_listener=ecs_prod_zone.shared_alb_listener
)


app.synth()
