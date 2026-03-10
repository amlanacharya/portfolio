"""Neo4j connector placeholder for readiness checks."""

from __future__ import annotations

from importlib import import_module


class Neo4jConnector:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self.uri = uri
        self.user = user
        self.password = password

    def is_configured(self) -> bool:
        return bool(self.uri and self.user and self.password)

    def ping(self) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "not_configured"

        try:
            neo4j = import_module("neo4j")
            driver = neo4j.GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            driver.verify_connectivity()
            driver.close()
            return True, "reachable"
        except ModuleNotFoundError:
            return False, "neo4j_driver_missing"
        except Exception as exc:  # pragma: no cover - driver/network dependent
            return False, str(exc)
