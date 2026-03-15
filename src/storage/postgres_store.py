from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import psycopg
except Exception:  # pragma: no cover
    psycopg = None  # type: ignore


@dataclass
class CitationMapEntry:
    canonical_id: str
    source_paper_id: str
    title: str
    year: int | None


class PostgresStore:
    """PostgreSQL persistence for SOA-CLI.

    This backend is designed as the primary metadata store while preserving
    local artifacts for backward compatibility with existing tooling.
    """

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.getenv("SOA_DB_DSN", "")
        self.enabled = bool(self.dsn and psycopg is not None)

    def _connect(self):
        if not self.enabled:
            raise RuntimeError("PostgresStore is disabled. Set SOA_DB_DSN and install psycopg.")
        return psycopg.connect(self.dsn)

    def init_schema(self, schema_path: Path | None = None) -> None:
        if not self.enabled:
            return
        schema_path = schema_path or Path("db/schema.sql")
        sql = schema_path.read_text(encoding="utf-8")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def ensure_run(self, topic: str = "") -> str:
        if not self.enabled:
            return ""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO runs (topic) VALUES (%s) RETURNING run_id",
                    (topic,),
                )
                run_id = str(cur.fetchone()[0])
            conn.commit()
        return run_id

    def finalize_run(self, run_id: str, status: str = "completed") -> None:
        if not self.enabled or not run_id:
            return
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE runs SET status=%s, finished_at=NOW() WHERE run_id=%s::uuid",
                    (status, run_id),
                )
            conn.commit()

    @staticmethod
    def _safe_year(value: Any) -> int | None:
        try:
            if value is None:
                return None
            year = int(str(value)[:4])
            if 1900 <= year <= 2100:
                return year
        except Exception:
            return None
        return None

    def sync_papers_and_aliases(self, extracted_dir: Path) -> list[CitationMapEntry]:
        """Upsert extracted papers and assign canonical IDs (P001...)."""
        entries: list[CitationMapEntry] = []

        extracted_files = sorted(extracted_dir.glob("*.json"))
        for idx, fp in enumerate(extracted_files, start=1):
            try:
                obj = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                obj = {}

            source_id = str(obj.get("paper_id") or fp.stem)
            canonical_id = f"P{idx:03d}"
            title = str(obj.get("title") or source_id)
            year = self._safe_year(obj.get("year"))
            venue = str(obj.get("venue") or obj.get("journal") or "")
            authors = obj.get("authors") if isinstance(obj.get("authors"), list) else []

            entries.append(CitationMapEntry(
                canonical_id=canonical_id,
                source_paper_id=source_id,
                title=title,
                year=year,
            ))

            if not self.enabled:
                continue

            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO papers (source_paper_id, canonical_paper_id, title, year, venue, authors, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                        ON CONFLICT (source_paper_id) DO UPDATE SET
                            canonical_paper_id=EXCLUDED.canonical_paper_id,
                            title=EXCLUDED.title,
                            year=EXCLUDED.year,
                            venue=EXCLUDED.venue,
                            authors=EXCLUDED.authors,
                            metadata=EXCLUDED.metadata,
                            updated_at=NOW()
                        RETURNING paper_pk
                        """,
                        (
                            source_id,
                            canonical_id,
                            title,
                            year,
                            venue,
                            json.dumps(authors, ensure_ascii=False),
                            json.dumps(obj, ensure_ascii=False),
                        ),
                    )
                    paper_pk = int(cur.fetchone()[0])
                    aliases = {source_id, fp.stem, canonical_id}
                    for alias in aliases:
                        cur.execute(
                            """
                            INSERT INTO paper_aliases (paper_pk, alias, source)
                            VALUES (%s, %s, 'auto')
                            ON CONFLICT (alias) DO NOTHING
                            """,
                            (paper_pk, alias),
                        )
                conn.commit()

        return entries

    def save_citation_map(self, entries: list[CitationMapEntry], path: Path) -> dict[str, Any]:
        payload = {
            "version": 1,
            "generated_by": "postgres_store",
            "entries": [
                {
                    "canonical_id": e.canonical_id,
                    "source_paper_id": e.source_paper_id,
                    "title": e.title,
                    "year": e.year,
                }
                for e in entries
            ],
            "canonical_to_source": {e.canonical_id: e.source_paper_id for e in entries},
            "source_to_canonical": {e.source_paper_id: e.canonical_id for e in entries},
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return payload

    def record_artifact(self, run_id: str, logical_name: str, artifact_type: str, local_path: str, content: str = "") -> None:
        if not self.enabled or not run_id:
            return
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO artifacts (run_id, logical_name, artifact_type, local_path, content)
                    VALUES (%s::uuid, %s, %s, %s, %s)
                    ON CONFLICT (run_id, logical_name) DO UPDATE SET
                        artifact_type=EXCLUDED.artifact_type,
                        local_path=EXCLUDED.local_path,
                        content=EXCLUDED.content
                    """,
                    (run_id, logical_name, artifact_type, local_path, content),
                )
            conn.commit()

    def record_metric(self, run_id: str, metric_name: str, metric_value: float | None, metric_json: dict[str, Any] | None = None) -> None:
        if not self.enabled or not run_id:
            return
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO metrics (run_id, metric_name, metric_value, metric_json)
                    VALUES (%s::uuid, %s, %s, %s::jsonb)
                    ON CONFLICT (run_id, metric_name) DO UPDATE SET
                        metric_value=EXCLUDED.metric_value,
                        metric_json=EXCLUDED.metric_json
                    """,
                    (run_id, metric_name, metric_value, json.dumps(metric_json or {}, ensure_ascii=False)),
                )
            conn.commit()

    def load_citation_map(self) -> dict[str, str]:
        if not self.enabled:
            return {}
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT canonical_paper_id, source_paper_id FROM papers WHERE canonical_paper_id IS NOT NULL"
                )
                rows = cur.fetchall()
        return {str(r[0]): str(r[1]) for r in rows}
