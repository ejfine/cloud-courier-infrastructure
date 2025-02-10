from .lib import ComputerLocation
from .lib import LabComputerConfig
from .lib import OnPremNode

CAMBRIDGE_LAB_NAME = ComputerLocation(name="cambridge")


def create_all_computers() -> list[OnPremNode]:
    all_computers: list[OnPremNode] = []

    all_computers.append(OnPremNode(LabComputerConfig(name="cytation-5", location=CAMBRIDGE_LAB_NAME)))

    return all_computers
