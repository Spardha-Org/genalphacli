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
from worker.workflows.generate_workflow import GenerateWorkflow
from worker.workflows.parse_workflow import ParseWorkflow

TEMPORAL_ADDRESS = os.environ.get("TEMPORAL_ADDRESS", "localhost:7233")

PARSE_QUEUE = "genalpha-parse"
GENERATE_QUEUE = "genalpha-generate"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """Start the Temporal worker with both parse and generate task queues."""
    logger.info("Connecting to Temporal at %s", TEMPORAL_ADDRESS)
    client = await Client.connect(TEMPORAL_ADDRESS)
    logger.info("Connected to Temporal")

    # Parse worker — conservative concurrency (clone is I/O heavy)
    parse_worker = Worker(
        client,
        task_queue=PARSE_QUEUE,
        workflows=[ParseWorkflow],
        activities=[
            clone_repo_activity,
            parse_routes_activity,
            cleanup_clone_activity,
        ],
        max_concurrent_activities=5,
    )

    # Generate worker — higher concurrency (generation is lightweight)
    generate_worker = Worker(
        client,
        task_queue=GENERATE_QUEUE,
        workflows=[GenerateWorkflow],
        activities=[
            generate_packages_activity,
            package_zip_activity,
        ],
        max_concurrent_activities=20,
    )

    logger.info("Starting workers: parse-queue (max 5), generate-queue (max 20)")

    # Run both workers concurrently
    async with parse_worker, generate_worker:
        await asyncio.gather(
            parse_worker.run(),
            generate_worker.run(),
        )


if __name__ == "__main__":
    asyncio.run(main())
