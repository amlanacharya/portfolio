"""Postgres connector placeholder for readiness checks."""

from __future__ import annotations

from importlib import import_module


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
