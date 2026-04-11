# TPS Migration Naming Convention

Based on the Java TPS Flyway pattern: `V<app_code>_<epoch>__<migration_type>.sql`

## Format

```
V<app_code>_<epoch>__<migration_type>.py
```

| Part | Description | Example |
|------|-------------|---------|
| `app_code` | App's stable integer ID. Use `0` for schema-level migrations. | `0`, `1`, `2` |
| `epoch` | Unix timestamp when migration was created | `1744343200` |
| `migration_type` | What the migration does (see types below) | `add_github_app_entity` |

## Migration Types

| Type | Pattern | When to use |
|------|---------|-------------|
| `create_tps_schema` | `V0_<epoch>__create_tps_schema` | Initial schema creation |
| `alter_tps_schema` | `V0_<epoch>__alter_<table>_<change>` | Schema changes (add/drop columns) |
| `add_<app>_app_entity` | `V<code>_<epoch>__add_<app>_app_entity` | Seed a new app into marketplace |
| `update_<app>_app_entity` | `V<code>_<epoch>__update_<app>_<change>` | Update an existing app's metadata |
| `add_<app>_actions` | `V<code>_<epoch>__add_<app>_actions` | Add actions for an app (future) |

## App Codes

| Code | App | Category |
|------|-----|----------|
| 0 | (schema) | — |
| 1 | GitHub | source_control |
| 2 | GitLab | source_control |
| 3 | Bitbucket | source_control |
| 10 | Cloudflare | hosting |
| 11 | Railway | hosting |
| 12 | Fly.io | hosting |
| 20 | PyPI | distribution |

## How to Create a Migration

```bash
# 1. Generate migration
uv run alembic revision --autogenerate -m "description"
# or for data-only:
uv run alembic revision -m "description"

# 2. Rename to convention
mv services/tps/migrations/versions/<hash>_description.py \
   services/tps/migrations/versions/V<app_code>_$(date +%s)__<migration_type>.py

# 3. Apply
uv run alembic upgrade head
```

## Example: Adding GitLab

```bash
# Create migration file
uv run alembic revision -m "add gitlab app entity"

# Rename
mv versions/<hash>_add_gitlab_app_entity.py versions/V2_1744400000__add_gitlab_app_entity.py

# Edit the file: add INSERT INTO tps_app_marketplace ...
# Apply
uv run alembic upgrade head
```
