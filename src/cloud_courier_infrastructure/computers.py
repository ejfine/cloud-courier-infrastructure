from .lib import AlertingConfig
from .lib import ComputerLocation
from .lib import FolderToWatch
from .lib import LabComputerConfig

CAMBRIDGE_LAB_NAME = ComputerLocation(name="Cambridge")
EMERYVILLE_LAB_NAME = ComputerLocation(name="Emeryville")


def create_all_computer_configs() -> list[LabComputerConfig]:
    all_computers: list[LabComputerConfig] = []

    all_computers.extend(
        [
            LabComputerConfig(
                name="Cytation-5",
                location=CAMBRIDGE_LAB_NAME,
                alerting_config=AlertingConfig(emails=["ejfine@gmail.com"]),
                folders_to_watch={"images": FolderToWatch(folder_path=r"C:\data\images")},
            )
        ]
    )

    return all_computers
