from __future__ import annotations

from dataclasses import dataclass

from SPARQLWrapper import SPARQLWrapper, JSON


@dataclass
class GraphDBConfig:
    base_url: str
    repository: str
    username: str | None = None
    password: str | None = None
    timeout_seconds: int = 15


class GraphDBClient:
    """Thin wrapper around GraphDB's SPARQL endpoint.

    Provides a minimal interface we can grow over time while keeping a clean
    separation of concerns (service class, testable, OOP-friendly).
    """

    def __init__(self, cfg: GraphDBConfig):
        endpoint = f"{cfg.base_url.rstrip('/')}/repositories/{cfg.repository}"
        self._sparql = SPARQLWrapper(endpoint)
        self._sparql.setReturnFormat(JSON)
        self._sparql.setTimeout(cfg.timeout_seconds)
        if cfg.username and cfg.password:
            self._sparql.setCredentials(cfg.username, cfg.password)

    def ping(self) -> bool:
        """Check connectivity by running a trivial ASK query.

        Returns True if the endpoint responds successfully, False otherwise.
        """
        try:
            self._sparql.setQuery("ASK {}")
            _ = self._sparql.query().convert()
            return True
        except Exception:
            return False

    def select(self, query: str) -> dict:
        """Execute a SELECT query and return the parsed JSON result."""
        self._sparql.setQuery(query)
        return self._sparql.query().convert()
