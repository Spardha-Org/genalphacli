"""Temporal worker entrypoint for genalphacli.

Run with: uv run --group worker python -m worker.worker
"""

from __future__ import annotations

import asyncio
import logging
import os

from temporalio.client import Client
from temporalio.worker import Worker

from worker.activities.generate_activities import (
    generate_packages_activity,
    package_zip_activity,
)
from worker.activities.github_activities import (
    cleanup_clone_activity,
    clone_repo_activity,
)
from worker.activities.parse_activities import parse_routes_activity
from worker.activities.status_activities import update_service_status
from worker.workflows.generate_workflow import GenerateWorkflow
from worker.workflows.parse_workflow import ParseWorkflow

TEMPORAL_ADDRESS = os.environ.get("TEMPORAL_ADDRESS", "localhost:7233")

PARSE_QUEUE = "genalpha-parse"
GENERATE_QUEUE = "genalpha-generate"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """Start the Temporal worker with both parse and generate task queues."""
    import concurrent.futures

    logger.info("Connecting to Temporal at %s", TEMPORAL_ADDRESS)
    client = await Client.connect(TEMPORAL_ADDRESS)
    logger.info("Connected to Temporal")

    # Thread pool for sync activities (clone, parse, generate are all sync)
    activity_executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

    # Single worker handling both parse and generate workflows
    worker = Worker(
        client,
        task_queue=PARSE_QUEUE,
        workflows=[ParseWorkflow, GenerateWorkflow],
        activities=[
            clone_repo_activity,
            parse_routes_activity,
            cleanup_clone_activity,
            update_service_status,
            generate_packages_activity,
            package_zip_activity,
        ],
        max_concurrent_activities=10,
        activity_executor=activity_executor,
    )

    logger.info("Starting worker on queue: %s", PARSE_QUEUE)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
