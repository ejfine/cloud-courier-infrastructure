from .lib import ComputerLocation
from .lib import LabComputerConfig

CAMBRIDGE_LAB_NAME = ComputerLocation(name="cambridge")


def create_all_computer_configs() -> list[LabComputerConfig]:
    all_computers: list[LabComputerConfig] = []

    all_computers.append(LabComputerConfig(name="cytation-5", location=CAMBRIDGE_LAB_NAME))

    return all_computers
