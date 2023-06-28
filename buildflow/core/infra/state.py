import dataclasses

from buildflow import utils
from buildflow.api.infra import InfraStatus


# TODO: Replace infra snapshots with this
@dataclasses.dataclass
class InfraState:
    status: InfraStatus
    timestamp_millis: int

    @classmethod
    def initial(cls) -> None:
        return None

    @classmethod
    def load(cls, infra_state_file_path: str) -> "InfraState":
        utils.assert_path_exists(infra_state_file_path)
        infra_state_dict = utils.read_json_file(infra_state_file_path)
        return cls(
            status=InfraStatus[infra_state_dict["status"]],
            timestamp_millis=infra_state_dict["timestamp_millis"],
        )

    def dump(self, infra_state_file_path: str):
        infra_state_dict = {
            "status": self.status.name,
            "timestamp_millis": self.timestamp_millis,
        }
        utils.write_json_file(infra_state_file_path, infra_state_dict)
