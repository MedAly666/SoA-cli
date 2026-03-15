#!/usr/bin/env python3
"""Initialize PostgreSQL schema for SOA-CLI."""

from pathlib import Path

from src.storage.postgres_store import PostgresStore


def main() -> None:
    store = PostgresStore()
    if not store.enabled:
        raise SystemExit("PostgresStore disabled. Set SOA_DB_DSN and install psycopg.")
    store.init_schema(Path("db/schema.sql"))
    print("[db] schema initialized")


if __name__ == "__main__":
    main()
