"""Temporal client — managed lifecycle, no global singletons."""

from __future__ import annotations

import logging
import time

from temporalio.client import Client

logger = logging.getLogger(__name__)

DEFAULT_TASK_QUEUE = "genalpha-parse"


class TemporalClient:
    """Wraps the Temporal SDK client with lifecycle management."""

    def __init__(self, client: Client):
        self._client = client

    @classmethod
    async def connect(cls, address: str) -> TemporalClient:
        logger.info("Connecting to Temporal at %s", address)
        client = await Client.connect(address)
        logger.info("Connected to Temporal")
        return cls(client)

    async def start_workflow(
        self,
        workflow_name: str,
        input_data: dict,
        service_id: str,
        prefix: str = "parse",
        task_queue: str = DEFAULT_TASK_QUEUE,
    ) -> str:
        """Start a Temporal workflow with an idempotent ID."""
        workflow_id = f"{prefix}-{service_id}-{int(time.time())}"
        await self._client.start_workflow(
            workflow_name,
            input_data,
            id=workflow_id,
            task_queue=task_queue,
        )
        logger.info("Started %s workflow %s", workflow_name, workflow_id)
        return workflow_id

    async def close(self):
        # Temporal Python SDK client doesn't have an explicit close
        pass
