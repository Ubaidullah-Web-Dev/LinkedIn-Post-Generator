import sqlite3
import os
import json
from datetime import datetime

class QueueManager:
    def __init__(self, db_path="automator.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    image_path TEXT,
                    status TEXT NOT NULL, -- DRAFT, QUEUED, POSTED, FAILED
                    scheduled_time TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def add_post(self, content, image_path, status, scheduled_time=None):
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO posts (content, image_path, status, scheduled_time, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (content, image_path, status, scheduled_time, now, now))
            conn.commit()
            return cursor.lastrowid

    def update_status(self, post_id, new_status):
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE posts SET status = ?, updated_at = ? WHERE id = ?
            """, (new_status, now, post_id))
            conn.commit()

    def get_pending_posts(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                SELECT * FROM posts 
                WHERE status = 'QUEUED' AND scheduled_time <= ?
                ORDER BY scheduled_time ASC
            """, (now,))
            return [dict(row) for row in cursor.fetchall()]

    def get_all_posts(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM posts ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]
