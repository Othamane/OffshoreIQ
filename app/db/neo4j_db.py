"""
Neo4j connection management.
Uses a singleton driver pattern with context manager support.
"""

from contextlib import contextmanager
from typing import Generator

from neo4j import GraphDatabase, Session
from neo4j.exceptions import ServiceUnavailable

from app.core.config import settings
from app.core.logging import logger


class Neo4jDatabase:
    """Manages the Neo4j driver lifecycle."""

    def __init__(self):
        self._driver = None

    def connect(self) -> None:
        logger.info("Connecting to Neo4j at %s", settings.neo4j_uri)
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        self._driver.verify_connectivity()
        logger.info("Neo4j connection established.")

    def close(self) -> None:
        if self._driver:
            self._driver.close()
            logger.info("Neo4j connection closed.")

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        if not self._driver:
            raise ServiceUnavailable("Neo4j driver not initialized.")
        with self._driver.session() as session:
            yield session

    def run_query(self, query: str, parameters: dict = None) -> list[dict]:
        """Execute a Cypher query and return results as a list of dicts."""
        with self.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]


# Singleton instance
db = Neo4jDatabase()
