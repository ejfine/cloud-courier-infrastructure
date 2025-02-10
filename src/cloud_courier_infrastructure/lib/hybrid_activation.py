from ephemeral_pulumi_deploy import append_resource_suffix
from pulumi import ComponentResource


class OnPremNode(ComponentResource):
    def __init__(
        self,
    ):
        super().__init__(
            "labauto:OnPrem",
            append_resource_suffix("raw-data-bucket"),
            None,
        )
