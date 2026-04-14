---
title: "feat: Add Temporal activity heartbeats for crash detection"
type: feat
status: active
date: 2026-04-14
---

# feat: Temporal Activity Heartbeats

## Problem

If the worker crashes mid-activity (during a 2-minute git clone or 3-minute publish), Temporal waits the full `start_to_close_timeout` before retrying. With heartbeats, Temporal detects the crash in ~30s and retries immediately.

## Implementation

### 1. Shared heartbeat utility

**File:** `worker/heartbeat.py`

Reusable context manager for blocking calls (git clone, subprocess, downloads):

```python
import contextvars
import threading
from contextlib import contextmanager
from temporalio import activity

@contextmanager
def heartbeat_periodically(interval: float = 10.0, message: str = "working"):
    ctx = contextvars.copy_context()
    stop = threading.Event()

    def _beat():
        while not stop.is_set():
            ctx.run(activity.heartbeat, message)
            stop.wait(interval)

    t = threading.Thread(target=_beat, daemon=True)
    t.start()
    try:
        yield
    finally:
        stop.set()
        t.join(timeout=2.0)
```

### 2. Activities to update

| Activity | Heartbeat points | Uses context manager? |
|----------|-----------------|----------------------|
| `clone_repo_activity` | fetch_token → fetch_info → cloning → detect_framework | Yes (git clone blocks) |
| `parse_routes_activity` | parsing | No (fast enough for checkpoints) |
| `fetch_pypi_sdist_activity` | fetch_info → download → extract → detect | Yes (download blocks) |
| `generate_packages_activity` | gen_cli → gen_mcp | No (fast) |
| `publish_to_pypi_activity` | fetch_token → build → upload_cli → upload_mcp | Yes (build + upload block) |
| `upload_artifact_activity` | before upload | No (single HTTP call) |
| `detect_auth_activity` | No change | Too fast (<1s) |
| `update_service_status` | No change | Too fast (<1s) |
| `cleanup_clone_activity` | No change | Too fast |
| `package_zip_activity` | No change | Fast |

### 3. Workflow heartbeat_timeout additions

Add `heartbeat_timeout` to `execute_activity` calls for long-running activities:

| Workflow | Activity | `start_to_close` | `heartbeat_timeout` (new) |
|----------|----------|-------------------|--------------------------|
| ParseWorkflow | clone_repo | 120s | 30s |
| ParseWorkflow | parse_routes | 180s | 30s |
| PyPIParseWorkflow | fetch_pypi_sdist | 120s | 30s |
| GenerateWorkflow | generate_packages | 120s | 30s |
| GenerateWorkflow | upload_artifact | 60s | 20s |
| PublishWorkflow | generate_packages | 120s | 30s |
| PublishWorkflow | publish_to_pypi | 180s | 30s |

### 4. File manifest

| File | Action |
|------|--------|
| `worker/heartbeat.py` | Create — shared heartbeat_periodically context manager |
| `worker/activities/github_activities.py` | Edit — add heartbeats to clone_repo_activity |
| `worker/activities/parse_activities.py` | Edit — add heartbeats to parse_routes_activity |
| `worker/activities/pypi_activities.py` | Edit — add heartbeats to fetch_pypi_sdist_activity |
| `worker/activities/generate_activities.py` | Edit — add heartbeats to generate + upload activities |
| `worker/activities/publish_activities.py` | Edit — add heartbeats to publish_to_pypi_activity |
| `worker/workflows/parse_workflow.py` | Edit — add heartbeat_timeout to execute_activity calls |
| `worker/workflows/pypi_parse_workflow.py` | Edit — same |
| `worker/workflows/generate_workflow.py` | Edit — same |
| `worker/workflows/publish_workflow.py` | Edit — same |

## Acceptance Criteria

- [ ] `heartbeat_periodically` context manager works with contextvars propagation
- [ ] clone_repo_activity heartbeats at each step + during git clone subprocess
- [ ] parse_routes_activity heartbeats before parsing
- [ ] fetch_pypi_sdist heartbeats during download + extraction
- [ ] publish_to_pypi heartbeats during build + each upload
- [ ] All 4 workflows have heartbeat_timeout on long-running activities
- [ ] Fast activities (<10s) are NOT modified (no overhead)
- [ ] Worker crash during clone → Temporal retries in ~30s (not 120s)
