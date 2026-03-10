"""Postgres connector and SQL helpers for deterministic data access."""

from __future__ import annotations

from contextlib import contextmanager
from importlib import import_module
from pathlib import Path
from typing import Any, Iterator


class PostgresConnector:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def is_configured(self) -> bool:
        return bool(self.dsn)

    def ping(self) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "not_configured"

        try:
            psycopg = import_module("psycopg")
            with psycopg.connect(self.dsn) as conn:
                conn.close()
            return True, "reachable"
        except ModuleNotFoundError:
            return False, "psycopg_driver_missing"
        except Exception as exc:  # pragma: no cover - driver/network dependent
            return False, str(exc)

    @contextmanager
    def connection(self) -> Iterator[Any]:
        if not self.is_configured():
            raise RuntimeError("postgres_not_configured")

        psycopg = import_module("psycopg")
        dict_row = import_module("psycopg.rows").dict_row
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            yield conn

    def execute_script(self, script_path: Path) -> None:
        sql_text = script_path.read_text(encoding="utf-8")
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_text)
            conn.commit()

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
            conn.commit()

    def executemany(self, sql: str, params: list[tuple[Any, ...]]) -> None:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, params)
            conn.commit()

    def fetch_one(self, sql: str, params: tuple[Any, ...] | None = None) -> dict[str, Any] | None:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                row = cur.fetchone()
            conn.commit()
        return row

    def fetch_all(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                rows = cur.fetchall()
            conn.commit()
        return rows
