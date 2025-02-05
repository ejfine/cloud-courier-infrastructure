from ephemeral_pulumi_deploy import append_resource_suffix
from pulumi import ComponentResource
from pulumi import ResourceOptions
from pulumi_aws_native import s3


class RawDataBucket(ComponentResource):
    def __init__(
        self,
    ):
        super().__init__(
            "labauto:AwsOrgWideRawDataBucket",
            append_resource_suffix("raw-data-bucket"),
            None,
        )
        _ = s3.Bucket(append_resource_suffix("raw-data-bucket"), opts=ResourceOptions(parent=self))
