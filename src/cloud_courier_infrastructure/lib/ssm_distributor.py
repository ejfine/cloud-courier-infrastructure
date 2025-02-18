import hashlib
import json
import os
from pathlib import Path
from tempfile import gettempdir
from urllib.parse import urlparse
from zipfile import ZipFile

import boto3
import pulumi
from ephemeral_pulumi_deploy import append_resource_suffix
from ephemeral_pulumi_deploy import get_aws_account_id
from ephemeral_pulumi_deploy import get_config_str
from pulumi import ComponentResource
from pulumi import Output
from pulumi import ResourceOptions
from pulumi_command import local
from pydantic import BaseModel

from .ssm_run_commands import add_boilerplate_to_ps_script


def get_central_infra_ssm_packages_bucket_name() -> str:
    org_home_region = get_config_str("proj:aws_org_home_region")
    ssm_client = boto3.client("ssm", region_name=org_home_region)
    bucket_param = ssm_client.get_parameter(Name="/org-managed/ssm-distributor-packages-bucket-name")["Parameter"]
    assert "Value" in bucket_param, f"Expected 'Value' in {bucket_param}"
    return bucket_param["Value"]


def get_sha256(file_path: Path) -> str:
    sha = hashlib.sha256()
    with file_path.open("rb") as file:
        for byte_block in iter(lambda: file.read(4096), b""):
            sha.update(byte_block)
    return sha.hexdigest()


class UploadFileToS3Command(ComponentResource):
    """Upload a file to S3."""

    def __init__(  # noqa: PLR0913 # yes, this is a lot of arguments, but they're all kwargs
        self,
        *,
        resource_name: str,
        bucket_name: Output[str],
        s3_key: str,
        bucket_region: str,
        local_file_path: Path,
        delete_on_destroy: bool = True,
        parent: ComponentResource,
    ) -> None:
        super().__init__(
            "labauto:UploadFileToS3",
            append_resource_suffix(resource_name),
            None,
        )
        file_hash = get_sha256(
            local_file_path
        )  # include the file hash in the create command so that if the local file changes, then it will be recognized and trigger an update of the resource
        _ = local.Command(
            append_resource_suffix(resource_name),
            create=bucket_name.apply(  # TODO: add tags to object
                lambda bucket_name: (
                    f"echo file hash: {file_hash} && aws s3api put-object --bucket {bucket_name} --key {s3_key} --body {local_file_path} --region {bucket_region}"
                )
            ),
            delete=bucket_name.apply(
                lambda bucket_name: (
                    f"aws s3api delete-object --bucket {bucket_name} --key {s3_key} --region {bucket_region}"
                    if delete_on_destroy
                    else ""
                )
            ),
            opts=ResourceOptions(
                parent=parent,
                replace_on_changes=[
                    "create",
                    "delete",
                ],  # Ensure that file is removed if anything changes.  otherwise it can be left in bucket which prevents deletion
                delete_before_replace=True,  # Since the file name is the same, ensure that it doesn't get deleted after being recreated during an update
            ),
        )


class DistributorFileToPackage(BaseModel):
    source_path: str
    local_name: str

    @property
    def is_s3_url(self) -> bool:
        return self.source_path.startswith("s3://")


def download_s3_file(*, file_to_package: DistributorFileToPackage, local_file_dir: Path, aws_region: str) -> Path:
    boto_session = boto3.Session()
    s3_client = boto_session.client("s3", region_name=aws_region)
    parsed_url = urlparse(
        file_to_package.source_path, allow_fragments=False
    )  # based on https://stackoverflow.com/questions/42641315/s3-urls-get-bucket-name-and-path
    local_path = local_file_dir / file_to_package.local_name
    s3_client.download_file(parsed_url.netloc, parsed_url.path.lstrip("/"), str(local_path))
    return local_path


class CloudCourierAgentInstaller(ComponentResource):
    def __init__(self, *, files_to_package: list[DistributorFileToPackage], version: str):
        super().__init__(
            "labauto:cloud-courier-agent-package",
            append_resource_suffix(),
            None,
        )
        package_base_name = "cloud-courier-agent"
        resource_name = f"{package_base_name}-{version}"
        org_home_region = get_config_str("proj:aws_org_home_region")
        temp_dir = Path(gettempdir()) / pulumi.get_project() / pulumi.get_stack() / resource_name
        temp_dir.mkdir(parents=True, exist_ok=True)
        zip_file_path = temp_dir / f"{resource_name}_WINDOWS.zip"
        pkg_install_file = temp_dir / "install.ps1"
        pkg_uninstall_file = temp_dir / "uninstall.ps1"
        files_to_zip: list[Path] = [pkg_install_file, pkg_uninstall_file]

        with pkg_install_file.open("w", encoding="utf-8") as file:
            _ = file.write(add_boilerplate_to_ps_script(self._generate_install_script()))
        with pkg_uninstall_file.open("w", encoding="utf-8") as file:
            _ = file.write(add_boilerplate_to_ps_script(self._generate_uninstall_script()))

        for file_to_package in files_to_package:
            if file_to_package.is_s3_url:
                files_to_zip.append(
                    download_s3_file(
                        file_to_package=file_to_package, local_file_dir=temp_dir, aws_region=org_home_region
                    )
                )
            else:
                raise NotImplementedError("Only S3 URLs are supported for now")

        with ZipFile(zip_file_path, "w") as archive:
            for file_path in files_to_zip:
                # Hard-code file timestamps so the final zip file/metadata remains the same checksum between builds
                os.utime(file_path, (1739893042, 1739893042))  # arbitrary timestamp
                os.chdir(file_path.parent)
                archive.write(file_path.name)

        pkg_manifest = {
            "schemaVersion": "2.0",
            "version": version,
            "packages": {"windows": {"_any": {"x86_64": {"file": zip_file_path.name}}}},
            "files": {zip_file_path.name: {"checksums": {"sha256": get_sha256(zip_file_path)}}},
        }

        dist_pkg_manifest_file_path = temp_dir / "manifest.json"
        with dist_pkg_manifest_file_path.open("w", encoding="utf-8") as file:
            _ = file.write(json.dumps(pkg_manifest))
        s3_key_prefix = f"{get_aws_account_id()}/{append_resource_suffix(package_base_name)}/v{version}"
        manifest_s3_key = f"{s3_key_prefix}/{dist_pkg_manifest_file_path.name}"
        pkg_s3_key = f"{s3_key_prefix}/{zip_file_path.name}"
        ssm_bucket_name = get_central_infra_ssm_packages_bucket_name()

        _ = UploadFileToS3Command(
            resource_name=f"{resource_name}-manifest",
            bucket_name=Output.from_input(ssm_bucket_name),
            s3_key=manifest_s3_key,
            bucket_region=org_home_region,
            local_file_path=dist_pkg_manifest_file_path,
            delete_on_destroy=False,
            parent=self,
        )
        _ = UploadFileToS3Command(
            resource_name=f"{resource_name}-package",
            bucket_name=Output.from_input(ssm_bucket_name),
            s3_key=pkg_s3_key,
            bucket_region=org_home_region,
            local_file_path=zip_file_path,
            delete_on_destroy=False,
            parent=self,
        )

    def _generate_install_script(self) -> str:
        return ""

    def _generate_uninstall_script(self) -> str:
        return ""
