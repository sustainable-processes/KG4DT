import aws_cdk as core
import aws_cdk.assertions as assertions

from stacks.workbench_stack import AwsDeploymentStack

# example tests. To run these tests, uncomment this file along with the example
# resource in aws_deployment/aws_deployment_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AwsDeploymentStack(app, "aws-deployment")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
