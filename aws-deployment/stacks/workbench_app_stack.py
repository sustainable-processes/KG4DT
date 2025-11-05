from aws_cdk import (
    Environment,
    Duration,
    aws_ecr as ecr,
    aws_codebuild as codebuild,
)
from constructs import Construct
from stacks.hosted_app_stack import HostedAppStack

import typing

# class WorkbenchAppStack(HostedAppStack):
#     WORKBENCH_IMAGE_SUFFIX = "workbench"
#     GRAPHDB_IMAGE_SUFFIX = "graphdb"

#     _repo_constructs: typing.Dict[str, ecr.Repository]

#     def __init__(self, scope: Construct, *, env: Environment) -> None:
#         super().__init__(scope, env=env, app_name="Workbench", github_repo_name="KG4DT") #check this value

#         self._repo_constructs = {}

#         source = codebuild.Source.git_hub(
#             owner=HostedAppStack.GIT_HUB_OWNER,
#             repo=self.github_repo_name,
#             webhook=True,
#             webhook_filters=[
#                 codebuild.FilterGroup
#                     .in_event_of(codebuild.EventAction.PUSH)
#                     .and_branch_is("main"),
#                 codebuild.FilterGroup
#                     .in_event_of(codebuild.EventAction.PUSH)
#                     .and_tag_is("prod"),
#             ]
#         )

#         build_env = {}
#         for suffix in [WorkbenchAppStack.WORKBENCH_IMAGE_SUFFIX, WorkbenchAppStack.GRAPHDB_IMAGE_SUFFIX]:
#             repo_name = self.app_name.lower() + "/" + suffix.lower()
#             repo = ecr.Repository(self, f"Repo-{suffix}",
#                 image_scan_on_push=True,
#                 image_tag_mutability=ecr.TagMutability.MUTABLE,
#                 repository_name=repo_name,
#                 lifecycle_rules=[
#                     ecr.LifecycleRule(tag_status=ecr.TagStatus.UNTAGGED, max_image_age=Duration.days(7)),
#                     ecr.LifecycleRule(tag_status=ecr.TagStatus.TAGGED, tag_pattern_list=["latest", "prod"], max_image_count=1),
#                     ecr.LifecycleRule(tag_status=ecr.TagStatus.TAGGED, tag_prefix_list=["git-"], max_image_age=Duration.days(30)),
#                 ],
#             )
#             env_var_name = f"{suffix.replace('-', '_').upper()}_REPO_URI"
#             build_env[env_var_name] = codebuild.BuildEnvironmentVariable(
#                 value=repo.repository_uri,
#                 type=codebuild.BuildEnvironmentVariableType.PLAINTEXT,
#             )
#             self._repo_constructs[suffix] = repo

#         project = codebuild.Project(self, f"Build-{self.github_repo_name}",
#             project_name=f"{self.github_repo_name}",
#             environment=codebuild.BuildEnvironment(
#                 compute_type=codebuild.ComputeType.LARGE,
#                 build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
#             ),
#             environment_variables={
#                 **build_env,
#                 "IMAGE_PLATFORM": codebuild.BuildEnvironmentVariable(
#                     value="linux/amd64",
#                     type=codebuild.BuildEnvironmentVariableType.PLAINTEXT,
#                 ),
#             },
#             build_spec=codebuild.BuildSpec.from_source_filename("buildspec.yaml"),
#             source=source,
#         )
#         for repo in self._repo_constructs.values():
#             repo.grant_push(project.role)

#     @property
#     def workbench_repo(self) -> ecr.Repository:
#         return self._repo_constructs[WorkbenchAppStack.WORKBENCH_IMAGE_SUFFIX]

#     @property
#     def graphdb_repo(self) -> ecr.Repository:
#         return self._repo_constructs[WorkbenchAppStack.GRAPHDB_IMAGE_SUFFIX]

from aws_cdk import (
    Stack,
    aws_ecr as ecr,
    Duration,
)
from constructs import Construct

class WorkbenchAppStack(Stack):
    WORKBENCH_IMAGE_SUFFIX = "workbench"
    GRAPHDB_IMAGE_SUFFIX = "graphdb"

    def __init__(self, scope: Construct, id: str, *, env=None, **kwargs) -> None:
        super().__init__(scope, id, env=env, **kwargs)

        # # Create ECR repositories for Workbench and GraphDB
        # self.workbench_repo = ecr.Repository(self, "WorkbenchRepo",
        #     repository_name="workbench",
        #     image_scan_on_push=True,
        #     lifecycle_rules=[
        #         ecr.LifecycleRule(tag_status=ecr.TagStatus.UNTAGGED, max_image_age=Duration.days(7)),
        #     ]
        # )

        # self.graphdb_repo = ecr.Repository(self, "GraphDBRepo",
        #     repository_name="graphdb",
        #     image_scan_on_push=True,
        #     lifecycle_rules=[
        #         ecr.LifecycleRule(tag_status=ecr.TagStatus.UNTAGGED, max_image_age=Duration.days(7)),
        #     ]
        # )

        self.workbench_repo = ecr.Repository.from_repository_name(
            self, "WorkbenchRepo", "workbench"
        )

        self.graphdb_repo = ecr.Repository.from_repository_name(
            self, "GraphDBRepo", "graphdb"
        )