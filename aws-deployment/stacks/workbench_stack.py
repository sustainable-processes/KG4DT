from aws_cdk import (
    Duration,
    Stack,
    Fn,
    RemovalPolicy,
    CfnOutput,
    Environment,
    aws_ec2 as ec2,
    aws_autoscaling as autoscaling,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_cognito as cognito,
    aws_logs as logs,
    aws_route53 as route53,
    aws_iam as iam
)
from constructs import Construct
from stacks.zone_stack import ZoneStack
from stacks.workbench_app_stack import WorkbenchAppStack
from stacks.knowledge_graph_stack import KnowledgeGraphStack
from stacks.cluster_stack import ClusterStack

class WorkbenchStack(Stack):
    def __init__(
            self,
            scope: Construct, 
            *, 
            env_name: str, 
            env: Environment,
            zone_stack: ZoneStack, 
            cluster_stack: ClusterStack,
            dns_zone_name: str,
            hosted_zone: route53.IHostedZone, 
            image_tag: str,
            webui_domain_name_prefix: str, 
            app_stack: WorkbenchAppStack,
            kg_stack: KnowledgeGraphStack,
            cert_stack,
            shared_alb: elbv2.IApplicationLoadBalancer,
            shared_alb_listener: elbv2.ApplicationListener
        ) -> None:
        super().__init__(scope, "Workbench" + env_name, env=env)

        webui_base_url = "https://" + webui_domain_name_prefix + "." + dns_zone_name

        # ===============================
        # Cognito authentication settings
        # ===============================

        user_pool_id = Fn.import_value("userPoolId")
        user_pool = cognito.UserPool.from_user_pool_id(self, "UserPool", user_pool_id)
        
        user_pool_client = user_pool.add_client("UserPoolClient",
            generate_secret=True,
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[cognito.OAuthScope.OPENID, cognito.OAuthScope.PROFILE],
                callback_urls=[webui_base_url + "/app/authorize"],
                logout_urls=[webui_base_url + "/app/index"]
            )
        )

        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)

        # ===============================
        # Auto Scaling Group Configuration
        # ===============================

        # ec2_sg = ec2.SecurityGroup(self, "WorkbenchEC2SG",
        #     vpc=zone_stack.vpc,
        #     allow_all_outbound=True
        # )
        
        # ec2_sg.add_ingress_rule(
        #     peer=ec2.Peer.ipv4(zone_stack.vpc.vpc_cidr_block),
        #     connection=ec2.Port.tcp(5000),
        #     description="Allow traffic on port 5000 from within the VPC"
        # )

        # asg = autoscaling.AutoScalingGroup(self, "WorkbenchASG",
        #     vpc=zone_stack.vpc,
        #     instance_type=ec2.InstanceType("t3.medium"),
        #     machine_image=ecs.EcsOptimizedImage.amazon_linux2(),
        #     min_capacity=1,
        #     max_capacity=5,
        #     desired_capacity=2,
        #     security_group=ec2_sg
        # )

        # ===============================
        # ECS Task Definition
        # ===============================

        task_definition = ecs.FargateTaskDefinition(self, "TaskDefinition",
            family="WorkbenchBackendTask" + env_name,
            cpu=2048,             # Match container's CPU
            memory_limit_mib=4096  # Match container's memory
        )

        container = task_definition.add_container("BackendContainer",
            image=ecs.ContainerImage.from_ecr_repository(app_stack.workbench_repo, image_tag),
            memory_limit_mib=4096,  # 2 GiB
            cpu=2048,               # 1 vCPU
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="WorkbenchBackend",
                log_group=logs.LogGroup(self, "LogGroup")
            ),
            environment={
                "GRAPHDB_HOST": "graphdb.default",
                "GRAPHDB_PORT": "7200",
                "COGNITO_REGION": user_pool.stack.region,
                "COGNITO_DOMAIN": Fn.import_value("userPoolDomain"),
                "COGNITO_USER_POOL_ID": user_pool.user_pool_id,
                "COGNITO_APP_CLIENT_ID": user_pool_client.user_pool_client_id,
                "COGNITO_APP_CLIENT_SECRET": user_pool_client.user_pool_client_secret.unsafe_unwrap(),
                "COGNITO_CALLBACK_URL": webui_base_url + "/app/authorize",
                "COGNITO_SIGNOUT_URL": webui_base_url + "/app/index",
                "SECRET_KEY": "b83c90d4ff22ef58c3aa184c1723a02f994c93d75583e3c7d48ae2d1ce05e61e",
                "COGNITO_SCOPE": "openid profile",
                "APP_PREFIX": "app"
            }
        )

        container.add_port_mappings(
            ecs.PortMapping(container_port=5000, name="backend-port")
        )

        # ===============================
        # ALB Security Group
        # ===============================

        backend_sg = ec2.SecurityGroup(self, "AlbSG",
            vpc=zone_stack.vpc,
            allow_all_outbound=True
        )

        backend_sg.connections.allow_to(
            cluster_stack.auto_scaling_instance_sg,
            ec2.Port.tcp_range(1024, 65535),
            "Allow ALB to ECS dynamic ports"
        )

        backend_sg.connections.allow_from(
            other=ec2.Peer.ipv4(zone_stack.vpc.vpc_cidr_block),
            port_range=ec2.Port.tcp(5000),
            description="Allow internal access to Workbench backend"
        )

        # ===============================
        # ECS Fargate Service Definition
        # ===============================

        service = ecs.FargateService(self, "Service",
            cluster=cluster_stack.cluster,
            task_definition=task_definition,
            desired_count=1,
            enable_execute_command=True,
            security_groups=[backend_sg],
            service_connect_configuration=ecs.ServiceConnectProps(
                namespace="default",
                services=[
                    ecs.ServiceConnectService(
                        discovery_name="workbench",
                        port_mapping_name="backend-port"
                    )
                ]
            )
        )


        # ===============================
        # Use shared ALB passed from cluster_stack
        # ===============================

        alb = shared_alb

        # HTTPS listener with certificate
        https_listener = shared_alb_listener

        workbench_tg = https_listener.add_targets("WorkbenchTargetGroup",
            port=5000,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[service],
            health_check=elbv2.HealthCheck(
                path="/app/health",
                port="traffic-port",
                protocol=elbv2.Protocol.HTTP,
                interval=Duration.seconds(30),
                timeout=Duration.seconds(10),
                healthy_http_codes="200-399",
                unhealthy_threshold_count=2,
                healthy_threshold_count=2
            )
        )

        https_listener.add_action("WorkbenchPathRule",
            priority=10,
            conditions=[elbv2.ListenerCondition.path_patterns(["/app*"])],
            action=elbv2.ListenerAction.forward([workbench_tg])
        )