from ephemeral_pulumi_deploy import append_resource_suffix
from pulumi import ComponentResource
from pulumi import ResourceOptions
from pulumi_aws_native import s3


class OnPremNode(ComponentResource):
    def __init__(
        self,
    ):
        super().__init__(
            "labauto:OnPrem",
            append_resource_suffix("raw-data-bucket"),
            None,
        )
        bucket = s3.Bucket(
            append_resource_suffix("raw-data-bucket"),
            opts=ResourceOptions(parent=self),
            versioning_configuration=s3.BucketVersioningConfigurationArgs(
                status=s3.BucketVersioningConfigurationStatus.ENABLED
            ),
        )
        self.bucket_name = bucket.id
