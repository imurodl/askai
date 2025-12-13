"""Database connection and operations module."""

import os
from typing import Optional, Dict, Any
from datetime import datetime
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Database:
    """PostgreSQL database connection and operations."""

    def __init__(self):
        """Initialize database connection parameters."""
        self.connection_params = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432"),
            "dbname": os.getenv("DB_NAME", "dinai"),
            "user": os.getenv("DB_USER", "dinai_user"),
            "password": os.getenv("DB_PASSWORD", "dinai_password"),
        }
        self._conn = None

    def connect(self):
        """Establish database connection."""
        if not self._conn or self._conn.closed:
            self._conn = psycopg.connect(**self.connection_params, row_factory=dict_row)
        return self._conn

    def close(self):
        """Close database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()

    def create_scrape_session(self, start_url: str) -> int:
        """Create a new scrape session.

        Args:
            start_url: The starting URL for scraping

        Returns:
            Session ID
        """
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO scrape_sessions (start_url, status, started_at)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (start_url, "running", datetime.now()),
            )
            session_id = cur.fetchone()["id"]
            conn.commit()
            return session_id

    def update_scrape_session(
        self,
        session_id: int,
        status: Optional[str] = None,
        pages_scraped: Optional[int] = None,
        last_scraped_url: Optional[str] = None,
        errors: Optional[str] = None,
    ):
        """Update scrape session information.

        Args:
            session_id: The session ID to update
            status: New status ('running', 'completed', 'failed')
            pages_scraped: Total number of pages scraped
            last_scraped_url: Last URL that was scraped
            errors: Error messages if any
        """
        conn = self.connect()
        with conn.cursor() as cur:
            updates = []
            params = []

            if status:
                updates.append("status = %s")
                params.append(status)
                if status in ("completed", "failed"):
                    updates.append("completed_at = %s")
                    params.append(datetime.now())

            if pages_scraped is not None:
                updates.append("pages_scraped = %s")
                params.append(pages_scraped)

            if last_scraped_url:
                updates.append("last_scraped_url = %s")
                params.append(last_scraped_url)

            if errors:
                updates.append("errors = %s")
                params.append(errors)

            if updates:
                params.append(session_id)
                query = f"UPDATE scrape_sessions SET {', '.join(updates)} WHERE id = %s"
                cur.execute(query, params)
                conn.commit()

    def insert_question(
        self,
        session_id: int,
        url: str,
        question_title: str,
        answer: str,
        question_text: Optional[str] = None,
        answer_author: Optional[str] = None,
        category: Optional[str] = None,
        published_date: Optional[str] = None,
        view_count: Optional[int] = None,
    ) -> Optional[int]:
        """Insert a new question into the database.

        Args:
            session_id: The scrape session ID
            url: Full URL of the question page
            question_title: Title of the question
            answer: The answer text
            question_text: Full question text (optional)
            answer_author: Author of the answer (optional)
            category: Question category (optional)
            published_date: Publication date (optional)
            view_count: View count (optional)

        Returns:
            Question ID if successful, None if duplicate
        """
        conn = self.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO questions 
                    (session_id, url, question_title, question_text, answer, 
                     answer_author, category, published_date, view_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        session_id,
                        url,
                        question_title,
                        question_text,
                        answer,
                        answer_author,
                        category,
                        published_date,
                        view_count,
                    ),
                )
                question_id = cur.fetchone()["id"]
                conn.commit()
                return question_id
        except psycopg.errors.UniqueViolation:
            conn.rollback()
            return None

    def insert_related_questions(
        self, question_id: int, related_questions: list
    ) -> int:
        """Insert related questions for a given question.

        Args:
            question_id: The ID of the main question
            related_questions: List of dicts with 'url', 'title', 'position'

        Returns:
            Number of related questions inserted
        """
        if not related_questions:
            return 0

        conn = self.connect()
        inserted_count = 0

        try:
            with conn.cursor() as cur:
                for rq in related_questions:
                    try:
                        cur.execute(
                            """
                            INSERT INTO related_questions 
                            (question_id, related_question_url, related_question_title, position)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (
                                question_id,
                                rq["url"],
                                rq["title"],
                                rq.get("position"),
                            ),
                        )
                        inserted_count += 1
                    except psycopg.errors.UniqueViolation:
                        # Skip duplicates
                        pass
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

        return inserted_count

    def question_exists(self, url: str) -> bool:
        """Check if a question URL already exists in the database.

        Args:
            url: The URL to check

        Returns:
            True if exists, False otherwise
        """
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM questions WHERE url = %s", (url,))
            return cur.fetchone() is not None

    def get_last_incomplete_session(self) -> Optional[Dict[str, Any]]:
        """Get the most recent incomplete scrape session.

        Returns:
            Dictionary with session data or None if no incomplete sessions
        """
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM scrape_sessions 
                WHERE status IN ('running', 'failed')
                ORDER BY started_at DESC
                LIMIT 1
                """
            )
            return cur.fetchone()

    def get_session_stats(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get statistics for a scrape session.

        Args:
            session_id: The session ID

        Returns:
            Dictionary with session stats or None if not found
        """
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM scrape_sessions WHERE id = %s", (session_id,))
            return cur.fetchone()
