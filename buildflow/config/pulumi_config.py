import dataclasses
import os
from typing import List, Mapping

from pulumi import automation as auto

from buildflow.config._config import Config


@dataclasses.dataclass
class PulumiStack(Config):
    name: str
    backend_url: str

    @classmethod
    def default(cls, *, pulumi_home_dir: str) -> Config:
        pulumi_local_stack_dir = os.path.join(pulumi_home_dir, "local")
        os.makedirs(pulumi_local_stack_dir, exist_ok=True)
        return cls(
            name="local",
            backend_url=f"file://{pulumi_local_stack_dir}",
        )

    @property
    def full_backend_url(self) -> str:
        if self.backend_url.startswith("file://"):
            base_path = self.backend_url.removeprefix("file://")
            abspath = os.path.abspath(base_path)
            return f"file://{abspath}"
        return self.backend_url


@dataclasses.dataclass
class PulumiConfig:
    project_name: str
    stacks: List[PulumiStack]
    pulumi_home: str

    @property
    def full_pulumi_home(self) -> str:
        return os.path.abspath(self.pulumi_home)

    _stacks: Mapping[str, PulumiStack] = dataclasses.field(init=False)

    def __post_init__(self):
        self._stacks = {s.name: s for s in self.stacks}

    def load(self):
        if not os.path.exists(self.full_pulumi_home):
            os.makedirs(self.full_pulumi_home, exist_ok=True)
        for stack in self.stacks:
            if stack.backend_url.startswith("file://"):
                base_path = stack.backend_url.removeprefix("file://")
                abspath = os.path.abspath(base_path)
                if not os.path.exists(abspath):
                    os.makedirs(abspath, exist_ok=True)

    @classmethod
    def default(cls, *, directory: str, project_name: str) -> "PulumiConfig":
        pulumi_home_dir = os.path.join(directory, ".buildflow", "_pulumi")
        os.makedirs(pulumi_home_dir, exist_ok=True)
        return cls(
            project_name=project_name,
            stacks=[PulumiStack.default(pulumi_home_dir=pulumi_home_dir)],
            pulumi_home=pulumi_home_dir,
        )

    def asdict(self):
        return {
            "stacks": [dataclasses.asdict(s) for s in self.stacks],
            "pulumi_home": self.pulumi_home,
        }

    def get_stack(self, stack: str) -> PulumiStack:
        return self._stacks[stack]

    def workspace_id(self, stack: str) -> str:
        if stack not in self._stacks:
            raise ValueError(f"Stack {stack} is not defined in the PulumiConfig")
        return f"{self.project_name}:{stack}"

    def stack_settings(self) -> auto.StackSettings:
        return auto.StackSettings(
            secrets_provider=None,
            encrypted_key=None,
            encryption_salt=None,
            config=None,
        )

    def project_settings(self, stack: PulumiStack) -> auto.ProjectSettings:
        return auto.ProjectSettings(
            name=self.project_name,
            runtime="python",
            main=None,
            description="Pulumi Project generated by Buildflow",
            author=None,
            website=None,
            license=None,
            config=None,
            template=None,
            backend=auto.ProjectBackend(stack.full_backend_url),
        )

    def workspace_options(self, stack: str) -> auto.LocalWorkspaceOptions:
        selected_stack = self.get_stack(stack)
        pulumi_passphrase = os.getenv("BUIDFLOW_PULUMI_PASSPHRASE", "buildflow")
        return auto.LocalWorkspaceOptions(
            work_dir=self.full_pulumi_home,
            pulumi_home=self.full_pulumi_home,
            # NOTE: we set the program as None here because we will be using an inline
            # `pulumi_program` function to dynamically create the program at runtime.
            program=None,
            env_vars={
                "PULUMI_CONFIG_PASSPHRASE": pulumi_passphrase,
            },
            # TODO: add support for `secrets_provider`
            secrets_provider=None,
            project_settings=self.project_settings(selected_stack),
            stack_settings={s.name: self.stack_settings() for s in self.stacks},
        )
