from aws_cdk import (
    Stack,
    Environment,
    aws_ecr as ecr,
    aws_codebuild as codebuild,
)
from constructs import Construct

import typing

class HostedAppStack(Stack):
    """
    A generic stack configuring AWS resources for an application hosted on AWS cloud
    having its sources in a single GitHub repo, its build and release pipelines in AWS,
    and its deployment target in an AWS account.
    """
    GIT_HUB_OWNER = "CDIdeveloper"

    def __init__(self, scope: Construct, *, 
            env: Environment,
            app_name: str,
            github_repo_name: str,
        ) -> None:
        """
        Initialize the stack.

        :param app_name: app name unique within the group, e.g., `JupyterHub`
        :param github_repo_name: GitHub repository under CDIdeveloper org for which to configure a build pipeline and ECR repos
        """
        super().__init__(scope, f"HostedApp{app_name}", env=env)

        self.app_name = app_name
        self.github_repo_name = github_repo_name