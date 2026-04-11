-- Create separate TPS database on first startup.
-- The default 'genalpha' DB is created by POSTGRES_DB env var.
-- This script runs once via docker-entrypoint-initdb.d.

SELECT 'CREATE DATABASE tps OWNER genalpha'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'tps')\gexec
