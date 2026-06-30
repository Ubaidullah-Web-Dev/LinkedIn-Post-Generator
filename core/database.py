"""
core/database.py — SQLite queue manager with WAL mode, migrations,
persistent connection, pagination, search, and stats.

v2 rewrite: fixes connection-per-call, ISO timestamp inconsistency,
missing indexes, no constraints, and adds migration versioning.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from core.constants import DB_PATH, PostStatus
from core.logger import get_logger

logger = get_logger(__name__)

# ── Helpers ─────────────────────────────────────────────────────────

def _now() -> str:
    """Consistent ISO timestamp without microseconds."""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def _unwrap_enum(val: Any) -> str:
    """Unwrap enum values correctly to strings."""
    return val.value if hasattr(val, "value") else str(val)


# ── Migrations ───────────────────────────────────────────────────────────────

_MIGRATIONS: list[str] = [
    # v2 additions
    "ALTER TABLE posts ADD COLUMN persona TEXT",
    "ALTER TABLE posts ADD COLUMN image_type TEXT",
    "ALTER TABLE posts ADD COLUMN char_count INTEGER",
    "ALTER TABLE posts ADD COLUMN error_log TEXT",
]


# ── QueueManager ─────────────────────────────────────────────────────────────

class QueueManager:
    """
    Singleton-pattern SQLite manager with WAL mode and schema migrations.

    Usage:
        db = QueueManager()        # uses default DB_PATH
        db = QueueManager(":memory:")  # for tests
    """

    _instances: dict[str, QueueManager] = {}

    def __new__(cls, db_path: str | Path = DB_PATH) -> QueueManager:
        key = str(db_path)
        if key not in cls._instances:
            inst = super().__new__(cls)
            inst._initialized = False
            cls._instances[key] = inst
        return cls._instances[key]

    def __init__(self, db_path: str | Path = DB_PATH) -> None:
        if self._initialized:
            return
        self._initialized = True
        self.db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    # ── Connection ───────────────────────────────────────────────────────

    def _get_connection(self) -> sqlite3.Connection:
        """Return persistent connection (create if needed). WAL mode enabled."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Close the persistent connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── Schema ───────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        """Create tables, indexes, and run migrations."""
        conn = self._get_connection()

        conn.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                image_path TEXT,
                status TEXT NOT NULL DEFAULT 'DRAFT'
                    CHECK(status IN ('DRAFT', 'QUEUED', 'POSTED', 'FAILED', 'DELETED')),
                scheduled_time TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                persona TEXT,
                image_type TEXT,
                char_count INTEGER,
                error_log TEXT
            )
        """)

        # Composite index for daemon polling
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_posts_status_scheduled
            ON posts(status, scheduled_time)
        """)

        # Index for recent-posts queries
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_posts_created
            ON posts(created_at DESC)
        """)

        conn.commit()

        # Run migrations for existing databases
        self._run_migrations()

    def _run_migrations(self) -> None:
        """Apply ALTER TABLE migrations idempotently."""
        conn = self._get_connection()
        for migration in _MIGRATIONS:
            try:
                conn.execute(migration)
            except sqlite3.OperationalError:
                pass  # Column already exists — expected
        conn.commit()

    def backup(self, suffix: str = "backup") -> Path | None:
        """Create a backup of the database file. Returns backup path."""
        src = Path(self.db_path)
        if not src.exists() or self.db_path == ":memory:":
            return None
        dest = src.with_suffix(f".{suffix}.db")
        try:
            shutil.copy2(src, dest)
            logger.info("Database backed up to %s", dest)
            return dest
        except OSError as e:
            logger.error("Failed to backup database: %s", e)
            return None

    # ── CRUD ─────────────────────────────────────────────────────────────

    def add_post(
        self,
        content: str,
        image_path: str | None = None,
        status: str = PostStatus.DRAFT,
        scheduled_time: str | None = None,
        persona: str | None = None,
        image_type: str | None = None,
    ) -> int:
        """Insert a new post. Returns the new row ID."""
        now = _now()
        conn = self._get_connection()
        cursor = conn.execute(
            """
            INSERT INTO posts
                (content, image_path, status, scheduled_time,
                 created_at, updated_at, persona, image_type, char_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (content, image_path, _unwrap_enum(status), scheduled_time,
             now, now, persona, image_type, len(content)),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def update_status(
        self, post_id: int, new_status: str, error_log: str | None = None
    ) -> None:
        """Update a post's status (and optionally log an error)."""
        now = _now()
        conn = self._get_connection()
        conn.execute(
            "UPDATE posts SET status = ?, updated_at = ?, error_log = ? WHERE id = ?",
            (_unwrap_enum(new_status), now, error_log, post_id),
        )
        conn.commit()

    def update_content(self, post_id: int, content: str) -> None:
        """Update a post's text content."""
        now = _now()
        conn = self._get_connection()
        conn.execute(
            "UPDATE posts SET content = ?, char_count = ?, updated_at = ? WHERE id = ?",
            (content, len(content), now, post_id),
        )
        conn.commit()

    def delete_post(self, post_id: int) -> None:
        """Soft-delete a post by setting status to DELETED."""
        self.update_status(post_id, PostStatus.DELETED)

    def hard_delete(self, post_id: int) -> None:
        """Permanently remove a post from the database."""
        conn = self._get_connection()
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()

    # ── Queries ──────────────────────────────────────────────────────────

    def get_post(self, post_id: int) -> dict[str, Any] | None:
        """Get a single post by ID."""
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        return dict(row) if row else None

    def get_posts(
        self,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get posts with pagination and optional status filter."""
        conn = self._get_connection()
        query = "SELECT * FROM posts"
        params: list[Any] = []

        conditions = ["status != 'DELETED'"]
        if status:
            conditions.append("status = ?")
            params.append(str(status))

        query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_post_summaries(
        self,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get lightweight post metadata (no full content) for table display."""
        conn = self._get_connection()
        query = """
            SELECT id, status, scheduled_time, char_count, persona, image_type,
                   created_at, updated_at, substr(content, 1, 80) as preview
            FROM posts
        """
        params: list[Any] = []

        conditions = ["status != 'DELETED'"]
        if status:
            conditions.append("status = ?")
            params.append(str(status))

        query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_pending_posts(self) -> list[dict[str, Any]]:
        """Get posts that are due for publishing."""
        now = _now()
        conn = self._get_connection()
        rows = conn.execute(
            """
            SELECT * FROM posts
            WHERE status = 'QUEUED' AND scheduled_time <= ?
            ORDER BY scheduled_time ASC
            """,
            (now,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_recent_content(self, count: int = 3) -> list[str]:
        """Get the last N post contents for AI context (duplicate prevention)."""
        conn = self._get_connection()
        rows = conn.execute(
            """
            SELECT substr(content, 1, 200) as snippet FROM posts
            WHERE status IN ('POSTED', 'QUEUED')
            ORDER BY created_at DESC LIMIT ?
            """,
            (count,),
        ).fetchall()
        return [r["snippet"] for r in rows]

    def search_posts(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search posts by content (LIKE matching)."""
        conn = self._get_connection()
        rows = conn.execute(
            """
            SELECT * FROM posts
            WHERE status != 'DELETED' AND content LIKE ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (f"%{query}%", limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Statistics ───────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, int]:
        """Return post counts by status + today's count."""
        conn = self._get_connection()

        total = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE status != 'DELETED'"
        ).fetchone()[0]

        counts: dict[str, int] = {"total": total}
        for status in ["DRAFT", "QUEUED", "POSTED", "FAILED"]:
            row = conn.execute(
                "SELECT COUNT(*) FROM posts WHERE status = ?", (status,)
            ).fetchone()
            counts[status.lower()] = row[0]

        # Posts today
        today = datetime.now().strftime("%Y-%m-%d")
        row = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE created_at LIKE ? AND status != 'DELETED'",
            (f"{today}%",),
        ).fetchone()
        counts["today"] = row[0]

        return counts

    # ── Compatibility alias ──────────────────────────────────────────────

    def get_all_posts(self) -> list[dict[str, Any]]:
        """Alias for backwards compatibility."""
        return self.get_posts(limit=500)
