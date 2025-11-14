from aws_cdk import (
    Duration,
    Stack,
    Environment,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_elasticloadbalancingv2_targets as elbv2_targets,
    aws_logs as logs,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
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
            shared_alb_listener: elbv2.ApplicationListener,
            fastapi_target_group: elbv2.ApplicationTargetGroup
        ) -> None:
        super().__init__(scope, "Workbench" + env_name, env=env)

        webui_base_url = "https://" + webui_domain_name_prefix + "." + dns_zone_name


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
            memory_limit_mib=2048,
            cpu=1024,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="FastAPI",
                log_group=logs.LogGroup(self, "LogGroup")
            ),
            environment={
                "GRAPHDB_HOST": "graphdb.default",
                "GRAPHDB_PORT": "7200"
            }
        )

        container.add_port_mappings(
            ecs.PortMapping(container_port=8000, name="backend-port")
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

        # Allow ALB to reach FastAPI on 8000
        backend_sg.connections.allow_from(
            other=shared_alb.connections.security_groups[0],
            port_range=ec2.Port.tcp(8000),
            description="Allow ALB access to FastAPI"
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

        # Register FastAPI ECS service into the shared FastAPI Target Group (default listener action)
        fastapi_target_group.add_target(
            elbv2_targets.EcsTarget(service, container_name="BackendContainer", port=8000)
        )

        # DNS record: kg4dt.cdi-sg.com -> ALB
        route53.ARecord(self, "Kg4dtAlias",
            zone=hosted_zone,
            # record_name=webui_domain_name_prefix,  # "kg4dt"
            target=route53.RecordTarget.from_alias(route53_targets.LoadBalancerTarget(shared_alb))
        )