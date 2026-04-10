"""Status update activity — notifies Core DB of workflow progress."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

import httpx
from temporalio import activity

logger = logging.getLogger(__name__)

CORE_URL = os.environ.get("CORE_URL", "http://localhost:8000")


@dataclass
class StatusUpdateInput:
    service_id: str
    status: str
    error_message: str | None = None
    framework: str | None = None
    route_graph: dict | None = None
    metadata: dict | None = None


@activity.defn
def update_service_status(input: StatusUpdateInput) -> None:
    """Update service status in Core DB via HTTP."""
    payload: dict = {"status": input.status}
    if input.error_message is not None:
        payload["error_message"] = input.error_message
    if input.framework is not None:
        payload["framework"] = input.framework
    if input.route_graph is not None:
        payload["route_graph"] = input.route_graph
    if input.metadata is not None:
        payload["metadata"] = input.metadata

    with httpx.Client(timeout=10.0) as client:
        response = client.post(
            f"{CORE_URL}/services/{input.service_id}/status",
            json=payload,
        )
        response.raise_for_status()

    logger.info("Updated service %s status to %s", input.service_id, input.status)
