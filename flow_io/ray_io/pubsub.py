"""IO connectors for Pub/Sub and Ray."""

import json
import logging
from typing import Any, Callable, Dict, Iterable, Union

import ray
from google.cloud import pubsub_v1

from flow_io import resources
from flow_io.ray_io import base
import time
import asyncio


@ray.remote
class PubSubSourceActor(base.RaySource):

    def __init__(
        self,
        ray_sinks: Iterable[base.RaySink],
        pubsub_ref: resources.PubSub,
    ) -> None:
        super().__init__(ray_sinks)
        self.subscription = pubsub_ref.subscription
        self.num_messages = 0
        self.start_time = time.time()
        self.max_messages = 1000

    def print_messages_per_second(self):
        print('Messages per second: ',
              self.num_messages / (time.time() - self.start_time))

    async def pull_messages(self, pubsub_client: pubsub_v1.SubscriberClient):
        return pubsub_client.pull(subscription=self.subscription,
                                  max_messages=self.max_messages)

    async def ack_messages(self, pubsub_client: pubsub_v1.SubscriberClient,
                           ack_ids: Iterable[str]):
        pubsub_client.acknowledge(ack_ids=ack_ids,
                                  subscription=self.subscription)

    async def run(self):
        with pubsub_v1.SubscriberClient() as pubsub_client:
            while True:
                # TODO: make this configurable
                response = await self.pull_messages(pubsub_client)

                ray_futures = []
                ack_ids = []
                for received_message in response.received_messages:
                    # TODO: maybe we should add the option to include the
                    # attributes. I believe beam provides that as an
                    # option.
                    decoded_data = received_message.message.data.decode()
                    json_loaded = json.loads(decoded_data)
                    for ray_sink in self.ray_sinks:
                        # TODO: add tracing context
                        process_ref = ray_sink.write.remote(json_loaded)
                        # TODO: support multiple sinks (rn it overwrites dict)
                        ray_futures.append(process_ref)
                        ack_ids.append(received_message.ack_id)

                # print('waiting in read')
                await asyncio.gather(*ray_futures)
                await self.ack_messages(pubsub_client, ack_ids)

                self.num_messages += len(ray_futures)
                self.print_messages_per_second()
                if self.num_messages > 10000 == 0:
                    self.num_messages = 0
                    self.start_time = time.time()


@ray.remote
class PubsubSinkActor(base.RaySink):

    def __init__(
        self,
        remote_fn: Callable,
        pubsub_ref: resources.PubSub,
    ) -> None:
        super().__init__(remote_fn)
        self.pubslisher_client = pubsub_v1.PublisherClient()
        self.topic = pubsub_ref.topic

    def _write(
        self,
        element: Union[Dict[str, Any], Iterable[Dict[str, Any]]],
    ):
        to_insert = element
        if isinstance(element, dict):
            to_insert = [element]
        for item in to_insert:
            future = self.pubslisher_client.publish(
                self.topic,
                json.dumps(item).encode('UTF-8'))
            future.result()
