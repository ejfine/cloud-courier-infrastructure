from ephemeral_pulumi_deploy import append_resource_suffix
from pulumi import ComponentResource


class RawDataBucket(ComponentResource):
    def __init__(
        self,
    ):
        super().__init__(
            "labauto:AwsRawDataBucket",
            append_resource_suffix("raw-data-bucket"),
            None,
        )
