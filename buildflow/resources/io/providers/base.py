import dataclasses
import pulumi
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional, Type


class AckInfo:
    pass


@dataclass(frozen=True)
class PullResponse:
    payload: Iterable[Any]
    ack_info: AckInfo


class ProviderAPI:
    def __init__(self):
        pass

    def schema(self):
        raise NotImplementedError("schema not implemented")


class SourceProvider(ProviderAPI):
    """PullProvider is a provider that can be pulled from.

    The following methods should be implemented:
        - pull()
        - ack()
        - backlog()
        - pull_converter()
        - max_batch_size()
    """

    def max_batch_size(self) -> int:
        """max_batch_size returns the max number of items that can be pulled at once."""
        raise NotImplementedError("max_batch_size not implemented")

    async def pull(self) -> PullResponse:
        """Pull returns a batch of data from the source."""
        raise NotImplementedError("pull not implemented")

    async def ack(self, to_ack: AckInfo, success: bool):
        """Ack acknowledges data pulled from the source.

        Args:
            to_ack: The ack info returned from the pull method. That should be acked.
            success: Whether the data was successfully processed or not. If false it is
                up to the provider to decide how to ack / nack.
        """
        raise NotImplementedError("ack not implemented")

    async def backlog(self) -> int:
        """Backlog returns an integer representing the number of items in the backlog"""
        raise NotImplementedError("backlog not implemented")

    def pull_converter(self, user_defined_type: Type) -> Callable[[Any], Any]:
        raise NotImplementedError("pull_converter not implemented")


class SinkProvider(ProviderAPI):
    """PushProvider is a provider that can have a batch of data pushed to it.

    The following methods should be implemented:
        - push()
        - push_converter()
    """

    async def push(self, batch):
        """Push pushes a batch of data to the source."""
        raise NotImplementedError("push not implemented")

    def push_converter(self, user_defined_type: Type) -> Callable[[Any], Any]:
        raise NotImplementedError("push_converter not implemented")


@dataclasses.dataclass
class PulumiResources:
    resources: Iterable[pulumi.Resource]
    exports: Dict[str, Any]


# NOTE: PulumiProviders set up resources at BUILD_TIME, not at RUNTIME.
class PulumiProvider(ProviderAPI):
    """PulumiProvider is a provider that sets up any resources needed using Pulumi.

    Pulumi Docs: https://www.pulumi.com/docs/

    Some Notes:
        - BuildFlow uses Pulumi "Inline Programs"
        - We do not currently support remote deployments (via pulumi cloud)
            - All deployments use the LocalWorkspace interface (from pulumi.automation)
        - Pulumi lets you "export" values from a resource so they can be viewed in the
          console output.

    The following methods should be implemented:
        - pulumi()
    """

    # NOTE: You can return anything that inherits from pulumi.Resource
    # (i.e. pulumi.ComponentResource)
    def pulumi(self, type_: Optional[Type]) -> PulumiResources:
        """Provides a list of pulumi.Resources to setup prior to runtime."""
        raise NotImplementedError("pulumi not implemented")
