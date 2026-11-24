"""
Database connection manager and schema migration runner for LibreSprite Learning & Skills.
Supports nested transactions via SQLite SAVEPOINTs and thread-local connection tracking.
"""

from __future__ import annotations

import contextlib
import os
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Generator, Optional, Union

DEFAULT_DB_PATH = Path("data/learning/learning.db")
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class DatabaseManager:
    """Manages SQLite connections, transactions, and schema setup with nested transaction support."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        if db_path is None:
            self.db_path = DEFAULT_DB_PATH
        elif str(db_path) == ":memory:":
            self.db_path = ":memory:"
        else:
            self.db_path = Path(db_path)

        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._local = threading.local()
        self._in_memory_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            # Keep a persistent connection for in-memory database
            self._in_memory_conn = self._create_connection()

        self.init_db()

    def _create_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.db_path) if self.db_path != ":memory:" else ":memory:",
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=False,
            isolation_level=None,  # Autocommit mode; transactions managed explicitly via BEGIN / SAVEPOINT
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def get_connection(self) -> sqlite3.Connection:
        """Returns the active transaction connection or a connection instance."""
        active_conn = getattr(self._local, "active_conn", None)
        if active_conn is not None:
            return active_conn
        if self._in_memory_conn is not None:
            return self._in_memory_conn
        return self._create_connection()

    @contextlib.contextmanager
    def transaction(
        self, conn: Optional[sqlite3.Connection] = None
    ) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager providing atomic transactions.
        Supports nesting via SQLite SAVEPOINTs.
        """
        # Case 1: An explicit connection was passed in
        if conn is not None:
            sp_name = f"sp_{uuid.uuid4().hex[:8]}"
            conn.execute(f"SAVEPOINT {sp_name}")
            try:
                yield conn
                conn.execute(f"RELEASE SAVEPOINT {sp_name}")
            except Exception:
                conn.execute(f"ROLLBACK TO SAVEPOINT {sp_name}")
                conn.execute(f"RELEASE SAVEPOINT {sp_name}")
                raise
            return

        # Case 2: An active transaction is already ongoing in this thread (nested transaction)
        active_conn = getattr(self._local, "active_conn", None)
        if active_conn is not None:
            sp_name = f"sp_{uuid.uuid4().hex[:8]}"
            active_conn.execute(f"SAVEPOINT {sp_name}")
            try:
                yield active_conn
                active_conn.execute(f"RELEASE SAVEPOINT {sp_name}")
            except Exception:
                active_conn.execute(f"ROLLBACK TO SAVEPOINT {sp_name}")
                active_conn.execute(f"RELEASE SAVEPOINT {sp_name}")
                raise
            return

        # Case 3: Top-level transaction
        connection = self.get_connection()
        self._local.active_conn = connection
        connection.execute("BEGIN IMMEDIATE")
        try:
            yield connection
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        finally:
            self._local.active_conn = None
            if self._in_memory_conn is None:
                connection.close()

    def init_db(self) -> None:
        """Executes all migration scripts in order."""
        if not MIGRATIONS_DIR.exists():
            return

        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        conn = self.get_connection()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS _schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            applied = {
                row["version"]
                for row in conn.execute("SELECT version FROM _schema_migrations").fetchall()
            }

            for mig in migration_files:
                version = mig.name
                if version not in applied:
                    with open(mig, "r", encoding="utf-8") as f:
                        sql = f.read()
                    conn.executescript(sql)
                    conn.execute(
                        "INSERT INTO _schema_migrations (version) VALUES (?)",
                        (version,),
                    )
        finally:
            if self._in_memory_conn is None:
                conn.close()

    def close(self) -> None:
        """Closes any persistent in-memory connection."""
        if self._in_memory_conn is not None:
            self._in_memory_conn.close()
            self._in_memory_conn = None
