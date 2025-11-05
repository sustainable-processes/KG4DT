from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_s3 as s3,
    aws_logs as logs,
    aws_elasticloadbalancingv2 as elbv2
)
from constructs import Construct
from stacks.zone_stack import ZoneStack
from stacks.cluster_stack import ClusterStack
from stacks.workbench_app_stack import WorkbenchAppStack

class KnowledgeGraphStack(Stack):
    def __init__(
        self,
        scope: Construct,
        *,
        env,
        env_name="Prod",
        zone_stack: ZoneStack,
        cluster: ClusterStack,
        image_tag: str,
        app_stack: WorkbenchAppStack
    ) -> None:
        super().__init__(scope, "KnowledgeGraphStack" + env_name, env=env)

        self.ontology_bucket = s3.Bucket(self, "OntologyBucket" + env_name,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY
        )

        task_definition = ecs.FargateTaskDefinition(self, "TaskDefinition",
            family="KnowledgeGraphTask" + env_name,
            cpu=512,
            memory_limit_mib=1024
        )

        container = task_definition.add_container(
            "KnowledgeGraphContainer",
            image=ecs.ContainerImage.from_ecr_repository(app_stack.graphdb_repo, image_tag),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="KnowledgeGraph",
                log_group=logs.LogGroup(self, "LogGroup",
                    removal_policy=RemovalPolicy.DESTROY
                )
            ),
            environment={
                "FLASK_DEBUG": "True",
                "ONTOLOGY_BUCKET": self.ontology_bucket.bucket_name
            }
        )

        container.add_port_mappings(
            ecs.PortMapping(container_port=7200, name="graphdb-port")
        )

        graphdb_sg = ec2.SecurityGroup(self, "GraphDBSG",
            vpc=zone_stack.vpc,
            description="Allow traffic to GraphDB from within VPC",
            allow_all_outbound=True
        )

        # Allow internal access on port 7200
        graphdb_sg.connections.allow_from(
            other=ec2.Peer.ipv4(zone_stack.vpc.vpc_cidr_block),
            port_range=ec2.Port.tcp(7200),
            description="Allow ECS services to reach GraphDB"
        )

        ecs_service = ecs.FargateService(self, "Service",
            cluster=cluster.cluster,
            task_definition=task_definition,
            desired_count=1,
            enable_execute_command=True,
            health_check_grace_period=Duration.minutes(5),
            security_groups=[graphdb_sg],
            service_connect_configuration=ecs.ServiceConnectProps(
                namespace="default",
                services=[ecs.ServiceConnectService(
                    port=7200,
                    discovery_name="graphdb",
                    port_mapping_name="graphdb-port"
                )]
            )
        )

        # Create target group for GraphDB
        graphdb_tg = cluster.shared_alb_listener.add_targets("GraphDBTargetGroup",
            port=7200,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[ecs_service],
            health_check=elbv2.HealthCheck(
                path="/repositories",
                port="traffic-port",
                protocol=elbv2.Protocol.HTTP,
                interval=Duration.seconds(30),
                timeout=Duration.seconds(10),
                healthy_http_codes="200-399",
                unhealthy_threshold_count=5,
                healthy_threshold_count=2
            )
        )

        # Add routing rule for path `/graphdb*`
        cluster.shared_alb_listener.add_action("GraphDBPathRule",
            priority=20,
            conditions=[elbv2.ListenerCondition.path_patterns(["/*"])],
            action=elbv2.ListenerAction.forward([graphdb_tg])
        )

        self.ontology_bucket.grant_read(task_definition.task_role)

        CfnOutput(self, "OntologyBucketName",
            value=self.ontology_bucket.bucket_name
        )