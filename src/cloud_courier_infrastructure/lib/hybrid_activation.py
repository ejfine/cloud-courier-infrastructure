import pulumi_aws
from ephemeral_pulumi_deploy import append_resource_suffix
from ephemeral_pulumi_deploy import common_tags
from ephemeral_pulumi_deploy import common_tags_native
from pulumi import ComponentResource
from pulumi import Output
from pulumi import ResourceOptions
from pulumi import export
from pulumi_aws.iam import GetPolicyDocumentStatementArgs
from pulumi_aws.iam import GetPolicyDocumentStatementConditionArgs
from pulumi_aws.iam import GetPolicyDocumentStatementPrincipalArgs
from pulumi_aws.iam import RolePolicy
from pulumi_aws.iam import get_policy_document
from pulumi_aws.ssm import Activation
from pulumi_aws_native import TagArgs
from pulumi_aws_native import iam

from .models import LabComputerConfig


def _generate_activation_script_contents(
    activation_id: str,
    activation_code: str,
) -> str:
    version = "3.3.1345.0"  # Latest version can be obtained from https://github.com/aws/amazon-ssm-agent/blob/mainline/RELEASENOTES.md
    region = pulumi_aws.config.region
    return (
        r"     $dir = $env:TEMP + '/ssm'; "
        r"New-Item -ItemType directory -Path $dir -Force; "
        r"$setupExe = $dir + '/AmazonSSMAgentSetup.exe'; "
        r"cd $dir; "
        rf"(New-Object System.Net.WebClient).DownloadFile('https://amazon-ssm-{region}.s3.{region}.amazonaws.com/{version}/windows_amd64/AmazonSSMAgentSetup.exe', $setupExe); "
        rf"Start-Process $setupExe -ArgumentList @('/q', '/log', 'install.log', 'CODE={activation_code}', 'ID={activation_id}', 'REGION={region}') -Wait; "
        # r"Get-Content ($env:ProgramData + '/Amazon/SSM/InstanceData/registration'); " # noqa: ERA001 (keeping the commented code since it was part of the original AWS script): including this fails the script unless it's run in Admin mode...and it doesn't seem super essential...all it does is display the managed instance ID and the AWS region
        r"Get-Service -Name 'AmazonSSMAgent';             "
    )


class OnPremNode(ComponentResource):
    def __init__(
        self,
        *,
        lab_computer_config: LabComputerConfig,
        ssm_logs_bucket_name: Output[str],
        data_bucket_name: Output[str],
    ):
        immutable_resource_name = lab_computer_config.immutable_full_resource_name
        resource_name = f"{lab_computer_config.location.name.lower()}--{lab_computer_config.name.lower()}"
        original_resource_name = lab_computer_config.original_resource_name

        super().__init__(
            "labauto:OnPremComputer",
            immutable_resource_name,
            None,
        )
        tags_native = [TagArgs(key="computer-info", value=resource_name), *common_tags_native()]

        role = iam.Role(
            immutable_resource_name,
            role_name=immutable_resource_name,
            opts=ResourceOptions(parent=self),
            assume_role_policy_document=get_policy_document(
                statements=[
                    # TODO: add permission for infrastructure testing role to assume this role
                    GetPolicyDocumentStatementArgs(
                        effect="Allow",
                        actions=["sts:AssumeRole"],
                        principals=[
                            GetPolicyDocumentStatementPrincipalArgs(type="Service", identifiers=["ssm.amazonaws.com"])
                        ],
                    )
                ]
            ).json,
            managed_policy_arns=["arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"],
            tags=tags_native,
        )
        _ = RolePolicy(  # the native provider has some CloudControl error when the policy document had an output in it
            append_resource_suffix(f"{resource_name}-upload-data", max_length=100),
            role=role.role_name,  # type: ignore[reportArgumentType] # pyright somehow thinks that a role_name can be None...which cannot happen
            name="upload-data",
            policy=data_bucket_name.apply(
                lambda bucket_name: get_policy_document(
                    statements=[
                        GetPolicyDocumentStatementArgs(
                            effect="Allow",
                            actions=["s3:PutObject"],
                            resources=[
                                f"arn:aws:s3:::{bucket_name}/{lab_computer_config.location.name.lower()}/{lab_computer_config.name.lower()}/*"
                            ],
                        ),
                    ]
                )
            ).json,
            opts=ResourceOptions(parent=self),
        )
        _ = RolePolicy(  # the native provider gave some odd CloudControl error about the policy, even though it has no Outputs in it
            append_resource_suffix(f"{resource_name}-put-cloudwatch-metrics", max_length=100),
            role=role.role_name,  # type: ignore[reportArgumentType] # pyright somehow thinks that a role_name can be None...which cannot happen
            name="put-cloudwatch-metrics",
            policy=get_policy_document(
                statements=[
                    GetPolicyDocumentStatementArgs(
                        sid="Heartbeat",
                        effect="Allow",
                        actions=["cloudwatch:PutMetricData"],
                        resources=["*"],
                        conditions=[
                            GetPolicyDocumentStatementConditionArgs(
                                test="StringEquals",
                                variable="cloudwatch:namespace",
                                values=["CloudCourier/Heartbeat"],
                            )
                        ],
                    ),
                ]
            ).json,
            opts=ResourceOptions(parent=self),
        )
        _ = RolePolicy(  # the native provider has some CloudControl error when the policy document had an output in it
            append_resource_suffix(f"{resource_name}-create-ssm-logs", max_length=100),
            role=role.role_name,  # type: ignore[reportArgumentType] # pyright somehow thinks that a role_name can be None...which cannot happen
            name="create-ssm-logs",
            policy=ssm_logs_bucket_name.apply(
                lambda bucket_name: get_policy_document(
                    statements=[
                        GetPolicyDocumentStatementArgs(
                            sid="CreateSSMLogs",
                            effect="Allow",
                            actions=["s3:GetEncryptionConfiguration"],
                            resources=[f"arn:aws:s3:::{bucket_name}"],
                        ),
                        GetPolicyDocumentStatementArgs(
                            sid="UploadSSMLogs",
                            effect="Allow",
                            actions=["s3:PutObject"],
                            resources=[f"arn:aws:s3:::{bucket_name}/*"],
                        ),
                    ]
                )
            ).json,
            opts=ResourceOptions(parent=self),
        )
        fixed_tags = common_tags()  # changes to the tags of the Activation will trigger replacement
        fixed_tags["original-computer-info"] = original_resource_name
        activation = Activation(
            immutable_resource_name,
            description=f"For the computer: {resource_name}.",
            iam_role=role.id,
            opts=ResourceOptions(parent=self),
            registration_limit=1,
            tags=fixed_tags,
            name=original_resource_name,
        )
        self.role_name = role.role_name
        export(
            f"-{original_resource_name}-activation-script",
            Output.all(activation.id, activation.activation_code).apply(
                lambda args: _generate_activation_script_contents(*args)
            ),
        )
