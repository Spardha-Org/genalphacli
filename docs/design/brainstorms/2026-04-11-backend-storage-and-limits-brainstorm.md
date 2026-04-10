---
date: 2026-04-11
topic: backend-storage-and-limits
---

# Backend: Storage & Limits Cleanup

## What We're Building

Two backend improvements to make the platform production-ready:

1. **Remove the 2-service-per-workspace limit** — currently enforced in `services/core/routes/parse.py:20`. No cap needed at this stage.

2. **Move generated ZIP packages from /tmp/ to PostgreSQL** — currently, the Generate workflow writes CLI/MCP ZIP packages to `/tmp/genalpha-zip-*/` and stores the filesystem path as `service.download_url`. This breaks on server restart, doesn't work in multi-instance deployments, and won't survive production. Store the binary in a new `core_artifacts` table instead.

## Why This Approach

### Remove limits entirely (not raise/tier)
- No billing system exists yet — tiers are premature
- The limit was a dev safety guard, not a product decision
- Can always add limits later when billing is built

### Store ZIPs in PostgreSQL (not S3)
- Generated packages are small (typically < 1MB)
- No extra infra needed — no S3 bucket, AWS credentials, or signed URLs
- Backup comes free with DB backups
- Simpler architecture for a project at this stage
- S3 can be added later if download volume or file sizes warrant it

### Separate artifacts table (not column on services)
- Keeps the `core_services` table lean — binary blobs won't slow down list queries
- Supports multiple artifacts per service (CLI zip + MCP zip stored separately)
- Each artifact has its own metadata (type, filename, size, created_at)

### Don't store cloned repos
- Clones are ephemeral — only needed during parsing, deleted after
- The `route_graph` JSON (the actual parsing output) is already stored in PostgreSQL as a `JSON` column on `core_services`
- Re-parsing triggers a fresh clone anyway, so caching old clones adds complexity for no benefit

## Key Decisions

- **Service limit**: Remove entirely — delete `MAX_SERVICES_PER_WORKSPACE` from both `parse.py` and `services.py`
- **ZIP storage**: New `core_artifacts` table with binary column (`LargeBinary`)
- **Artifact types**: `cli`, `mcp` — one row per generated package
- **Download URL**: Replace filesystem path (`/tmp/...`) with a Core API endpoint (`GET /artifacts/{id}/download`) that streams the binary from DB
- **Cloned repos**: Keep ephemeral (clone → parse → delete). No change needed.
- **`download_url` column**: Remove from `core_services` — replaced by the artifacts table and download endpoint
- **route_graph**: Already in DB as JSON. No change needed.

## Schema: `core_artifacts`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `service_id` | UUID FK | References `core_services.id`, cascade delete |
| `artifact_type` | String | `"cli"` or `"mcp"` |
| `filename` | String | e.g. `"my-api-cli.zip"` |
| `file_data` | LargeBinary | The ZIP bytes |
| `file_size` | Integer | Size in bytes |
| `created_at` | DateTime | Timestamp |

## Resolved Questions

- **Store repos in DB?** No — repos are ephemeral, only the parsed `route_graph` JSON matters, and it's already in the DB.
- **S3 vs DB for ZIPs?** DB — packages are small, no extra infra needed at this stage.
- **Single column vs separate table?** Separate `core_artifacts` table — supports multiple artifacts per service and keeps services table lean.

## Next Steps

-> `/workflows:plan` for implementation details
