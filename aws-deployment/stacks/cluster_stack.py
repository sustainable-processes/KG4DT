from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_autoscaling as autoscaling,
    aws_elasticloadbalancingv2 as elbv2,
)
from constructs import Construct
from stacks.zone_stack import ZoneStack
from stacks.cert_stack import CertStack

class ClusterStack(Stack):
    def __init__(self, scope: Construct, id: str, *, env, env_name: str, zone_stack: ZoneStack, cert_stack: CertStack) -> None:
        super().__init__(scope, id, env=env)

        # Create the ECS Cluster
        self.cluster = ecs.Cluster(self, "Cluster",
            cluster_name="SharedCluster" + env_name,
            vpc=zone_stack.vpc
        )

        self.cluster.add_default_cloud_map_namespace(
            name="default",
            vpc=zone_stack.vpc
        )

        # Security Group for ECS Instances
        self.auto_scaling_instance_sg = ec2.SecurityGroup(self, "AutoScalingGroupSG",
            allow_all_outbound=True,
            vpc=zone_stack.vpc
        )
        self.auto_scaling_instance_sg.add_ingress_rule(ec2.Peer.ipv4(zone_stack.vpc.vpc_cidr_block), ec2.Port.all_traffic())

        # Auto Scaling Group (ASG) for ECS
        auto_scaling_group = autoscaling.AutoScalingGroup(self, "AutoScalingGroup",
            vpc=zone_stack.vpc,
            instance_type=ec2.InstanceType("t3a.large"),
            machine_image=ecs.EcsOptimizedImage.amazon_linux2(),
            min_capacity=1,
            max_capacity=2,
            vpc_subnets=ec2.SubnetSelection(subnet_group_name="Application"),
            security_group=self.auto_scaling_instance_sg
        )

        # ECS Capacity Provider
        capacity_provider = ecs.AsgCapacityProvider(self, "CapacityProvider",
            auto_scaling_group=auto_scaling_group
        )

        self.cluster.add_asg_capacity_provider(capacity_provider)

        # Shared Application Load Balancer
        self.shared_alb = elbv2.ApplicationLoadBalancer(self, "SharedALB",
            vpc=zone_stack.vpc,
            internet_facing=True,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
        )

        self.shared_alb_listener = self.shared_alb.add_listener("Listener",
            port=443,
            certificates=[cert_stack.web_cert],
            default_action=elbv2.ListenerAction.fixed_response(
                status_code=200,
                message_body="Shared ALB HTTPS listener active",
                content_type="text/plain"
            )
        )