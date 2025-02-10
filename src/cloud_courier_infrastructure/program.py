import logging

from ephemeral_pulumi_deploy import get_aws_account_id
from ephemeral_pulumi_deploy import get_config
from pulumi import export

from .computers import create_all_computer_configs
from .lib import OnPremNode
from .lib import RawDataBucket
from .lib import SsmLogsBucket

logger = logging.getLogger(__name__)


def pulumi_program() -> None:
    """Execute creating the stack."""
    env = get_config("proj:env")
    export("env", env)
    aws_account_id = get_aws_account_id()
    export("aws-account-id", aws_account_id)

    # Create Resources Here
    # TODO: add ability for custom bucket lifecycle policy
    # TODO: add ability for customization of the bucket policy
    _ = RawDataBucket()
    ssm_logs_bucket = SsmLogsBucket()
    all_computer_configs = create_all_computer_configs()
    for computer_config in all_computer_configs:
        _ = OnPremNode(lab_computer_config=computer_config, ssm_logs_bucket_name=ssm_logs_bucket.bucket_name)
