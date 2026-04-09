"""Route parsing activity — wraps the existing genalphacli pipeline."""

from __future__ import annotations

import logging
from pathlib import Path

from temporalio import activity

from genalphacli.pipeline import run_pipeline
from worker.activities.schemas import ParseRoutesInput, ParseRoutesOutput

logger = logging.getLogger(__name__)


@activity.defn
def parse_routes_activity(input: ParseRoutesInput) -> ParseRoutesOutput:
    """Parse API routes from a cloned repository.

    Wraps genalphacli.pipeline.run_pipeline() as a Temporal activity.
    Uses plain def (not async def) because the pipeline is CPU-bound/synchronous.
    Temporal runs sync activities in a thread pool automatically.
    """
    clone_path = Path(input.clone_dir)
    logger.info("Parsing routes from %s (framework=%s)", clone_path, input.framework)

    graph = run_pipeline(
        repo_root=clone_path,
        framework=input.framework,
        command_name=input.command_name,
    )

    # Convert Pydantic model to dict at the Temporal boundary
    route_graph = graph.model_dump()
    warnings = [w.message for w in graph.metadata.warnings]

    logger.info(
        "Parsed %d routes in %dms (%d warnings)",
        graph.metadata.total_routes,
        graph.metadata.parse_time_ms,
        len(warnings),
    )

    return ParseRoutesOutput(
        route_graph=route_graph,
        route_count=graph.metadata.total_routes,
        parse_time_ms=graph.metadata.parse_time_ms,
        warnings=warnings,
    )
