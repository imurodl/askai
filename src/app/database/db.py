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
        """Insert a new question or update a placeholder.

        If the URL already exists as a placeholder (is_fully_scraped = false),
        this method will update it with full data and mark it as fully scraped.

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
            Question ID if successful, None if already fully scraped
        """
        conn = self.connect()
        try:
            with conn.cursor() as cur:
                # Check if URL exists and if it's a placeholder
                cur.execute(
                    "SELECT id, is_fully_scraped FROM questions WHERE url = %s",
                    (url,)
                )
                existing = cur.fetchone()

                if existing:
                    if existing["is_fully_scraped"]:
                        # Already fully scraped, don't update
                        return None
                    else:
                        # Update placeholder with full data
                        cur.execute(
                            """
                            UPDATE questions
                            SET session_id = %s,
                                question_title = %s,
                                question_text = %s,
                                answer = %s,
                                answer_author = %s,
                                category = %s,
                                published_date = %s,
                                view_count = %s,
                                is_fully_scraped = true,
                                scraped_at = NOW()
                            WHERE id = %s
                            RETURNING id
                            """,
                            (
                                session_id,
                                question_title,
                                question_text,
                                answer,
                                answer_author,
                                category,
                                published_date,
                                view_count,
                                existing["id"],
                            ),
                        )
                        question_id = cur.fetchone()["id"]
                        conn.commit()
                        return question_id
                else:
                    # Insert new question (marked as fully scraped)
                    cur.execute(
                        """
                        INSERT INTO questions
                        (session_id, url, question_title, question_text, answer,
                         answer_author, category, published_date, view_count, is_fully_scraped)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, true)
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
        """Insert related questions using many-to-many relationship.

        For each related question:
        1. Check if it exists in questions table
        2. If not, create a placeholder with is_fully_scraped = false
        3. Create relationship in question_relationships junction table

        Args:
            question_id: The ID of the main question
            related_questions: List of dicts with 'url', 'title', 'position'

        Returns:
            Number of relationships inserted
        """
        if not related_questions:
            return 0

        conn = self.connect()
        inserted_count = 0

        try:
            with conn.cursor() as cur:
                # Get the placeholder session ID
                cur.execute(
                    "SELECT id FROM scrape_sessions WHERE start_url = %s LIMIT 1",
                    ("placeholder",)
                )
                placeholder_session = cur.fetchone()
                placeholder_session_id = placeholder_session["id"] if placeholder_session else None

                if not placeholder_session_id:
                    # Create placeholder session if it doesn't exist
                    cur.execute(
                        """
                        INSERT INTO scrape_sessions (start_url, status, started_at, pages_scraped)
                        VALUES (%s, %s, NOW(), 0)
                        RETURNING id
                        """,
                        ("placeholder", "completed")
                    )
                    placeholder_session_id = cur.fetchone()["id"]

                for rq in related_questions:
                    related_url = rq["url"]
                    related_title = rq["title"]
                    position = rq.get("position")

                    # Check if related question exists
                    cur.execute(
                        "SELECT id FROM questions WHERE url = %s",
                        (related_url,)
                    )
                    result = cur.fetchone()

                    if result:
                        # Question exists, get its ID
                        related_question_id = result["id"]
                    else:
                        # Create placeholder question
                        cur.execute(
                            """
                            INSERT INTO questions
                            (url, question_title, question_text, answer, is_fully_scraped, session_id)
                            VALUES (%s, %s, '', '', false, %s)
                            ON CONFLICT (url) DO UPDATE SET url = EXCLUDED.url
                            RETURNING id
                            """,
                            (related_url, related_title, placeholder_session_id)
                        )
                        related_question_id = cur.fetchone()["id"]

                    # Insert relationship into junction table
                    try:
                        cur.execute(
                            """
                            INSERT INTO question_relationships
                            (question_id, related_question_id, position)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (question_id, related_question_id) DO NOTHING
                            """,
                            (question_id, related_question_id, position)
                        )
                        if cur.rowcount > 0:
                            inserted_count += 1
                    except psycopg.errors.UniqueViolation:
                        # Skip duplicate relationships
                        pass

                conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

        return inserted_count

    def question_exists(self, url: str) -> bool:
        """Check if a question URL already exists and is fully scraped.

        Args:
            url: The URL to check

        Returns:
            True if exists and fully scraped, False otherwise
        """
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM questions WHERE url = %s AND is_fully_scraped = true",
                (url,)
            )
            return cur.fetchone() is not None

    def get_question_id_by_url(self, url: str) -> Optional[int]:
        """Get question ID by URL.

        Args:
            url: The URL to look up

        Returns:
            Question ID if found, None otherwise
        """
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM questions WHERE url = %s", (url,))
            result = cur.fetchone()
            return result["id"] if result else None

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

    def get_highest_question_url(self) -> Optional[str]:
        """Get the highest numbered question URL from the database.

        Returns:
            The URL with the highest number (e.g., '/s/8293') or None if no questions
        """
        conn = self.connect()
        with conn.cursor() as cur:
            # Extract number from URL pattern /s/NUMBER and find the max
            # Only consider fully scraped questions (not placeholder related questions)
            cur.execute(
                """
                SELECT url FROM questions
                WHERE url ~ '^/s/[0-9]+$'
                AND is_fully_scraped = true
                ORDER BY CAST(SUBSTRING(url FROM '/s/([0-9]+)') AS INTEGER) DESC
                LIMIT 1
                """
            )
            result = cur.fetchone()
            return result["url"] if result else None

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

    # ========================================================================
    # Fatvo.uz Scraper Methods
    # ========================================================================

    def insert_fatvo_category(
        self,
        category_id: str,
        name_cyr: Optional[str] = None,
        name_lat: Optional[str] = None,
        created: Optional[str] = None,
        updated: Optional[str] = None,
    ) -> Optional[int]:
        """Insert a fatvo.uz category.

        Args:
            category_id: Category ID from API
            name_cyr: Category name in Cyrillic
            name_lat: Category name in Latin
            created: Created timestamp from API
            updated: Updated timestamp from API

        Returns:
            Category ID if successful, None if already exists
        """
        conn = self.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO fatvo_categories
                    (category_id, name_cyr, name_lat, created, updated)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (category_id, name_cyr, name_lat, created, updated),
                )
                result = cur.fetchone()
                conn.commit()
                return result["id"] if result else None
        except psycopg.errors.UniqueViolation:
            conn.rollback()
            return None

    def fatvo_category_exists(self, category_id: str) -> bool:
        """Check if a fatvo.uz category exists.

        Args:
            category_id: Category ID to check

        Returns:
            True if exists, False otherwise
        """
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM fatvo_categories WHERE category_id = %s", (category_id,)
            )
            return cur.fetchone() is not None

    def insert_fatvo_question(
        self,
        question_id: str,
        session_id: int,
        qid: Optional[int] = None,
        category_id: Optional[str] = None,
        title_cyr: Optional[str] = None,
        title_lat: Optional[str] = None,
        question_cyr: Optional[str] = None,
        question_lat: Optional[str] = None,
        answer_cyr: Optional[str] = None,
        answer_lat: Optional[str] = None,
        answered_by: Optional[str] = None,
        answered_time: Optional[str] = None,
        status: Optional[str] = None,
        scope: Optional[str] = None,
        views: Optional[int] = None,
        created: Optional[str] = None,
        updated: Optional[str] = None,
    ) -> Optional[int]:
        """Insert a fatvo.uz question.

        Args:
            question_id: Question ID from API (unique identifier)
            session_id: Scrape session ID
            qid: Sequential question number from API
            category_id: Category ID
            title_cyr: Title in Cyrillic
            title_lat: Title in Latin
            question_cyr: Question text in Cyrillic
            question_lat: Question text in Latin
            answer_cyr: Answer text in Cyrillic
            answer_lat: Answer text in Latin
            answered_by: User ID who answered
            answered_time: When answered (timestamp)
            status: Question status (answered, pending, etc.)
            scope: Scope (public, private)
            views: View count
            created: Created timestamp from API
            updated: Updated timestamp from API

        Returns:
            Question ID if successful, None if already exists
        """
        conn = self.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO fatvo_questions
                    (question_id, session_id, qid, category_id,
                     title_cyr, title_lat, question_cyr, question_lat,
                     answer_cyr, answer_lat, answered_by, answered_time,
                     status, scope, views, created, updated)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        question_id,
                        session_id,
                        qid,
                        category_id,
                        title_cyr,
                        title_lat,
                        question_cyr,
                        question_lat,
                        answer_cyr,
                        answer_lat,
                        answered_by,
                        answered_time,
                        status,
                        scope,
                        views,
                        created,
                        updated,
                    ),
                )
                result = cur.fetchone()
                conn.commit()
                return result["id"] if result else None
        except psycopg.errors.UniqueViolation:
            conn.rollback()
            return None

    def fatvo_question_exists(self, question_id: str) -> bool:
        """Check if a fatvo.uz question exists.

        Args:
            question_id: Question ID to check

        Returns:
            True if exists, False otherwise
        """
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM fatvo_questions WHERE question_id = %s", (question_id,)
            )
            return cur.fetchone() is not None

    def get_fatvo_last_page(self, session_id: int) -> int:
        """Get the last scraped page number for a fatvo session.

        Args:
            session_id: Session ID

        Returns:
            Last page number, or 0 if not found
        """
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT last_scraped_url FROM scrape_sessions WHERE id = %s",
                (session_id,),
            )
            result = cur.fetchone()
            if result and result["last_scraped_url"]:
                # Parse "page:15" format
                last_url = result["last_scraped_url"]
                if ":" in last_url:
                    try:
                        return int(last_url.split(":")[1])
                    except (ValueError, IndexError):
                        return 0
            return 0

    # ========================================================================
    # Session and Chat History Methods
    # ========================================================================

    def upsert_session(
        self,
        session_id: str,
        user_agent: Optional[str] = None,
        device_type: Optional[str] = None,
        language: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """Create or update a session.

        Args:
            session_id: UUID string from client
            user_agent: Browser user agent
            device_type: 'mobile', 'desktop', or 'tablet'
            language: Browser language code
            ip_address: Client IP address

        Returns:
            True if created, False if updated
        """
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sessions (id, user_agent, device_type, language, ip_address)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    last_active_at = NOW()
                RETURNING (xmax = 0) AS inserted
                """,
                (session_id, user_agent, device_type, language, ip_address),
            )
            result = cur.fetchone()
            conn.commit()
            return result["inserted"]

    def insert_chat_message(
        self,
        session_id: str,
        question: str,
        answer: str,
        source_type: str,
        sources: Optional[list] = None,
        keywords: Optional[list] = None,
        response_time_ms: Optional[int] = None,
    ) -> int:
        """Insert a chat message.

        Args:
            session_id: Session UUID
            question: User's question text
            answer: AI response text
            source_type: 'database', 'ai_knowledge', or 'conversational'
            sources: List of source dicts [{id, title, relevance}, ...]
            keywords: List of extracted keywords
            response_time_ms: Response time in milliseconds

        Returns:
            Chat message ID
        """
        import json
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat
                (session_id, question, answer, source_type, sources, keywords, response_time_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    session_id,
                    question,
                    answer,
                    source_type,
                    json.dumps(sources or []),
                    keywords or [],
                    response_time_ms,
                ),
            )
            result = cur.fetchone()
            conn.commit()
            return result["id"]

    def get_chat_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list:
        """Get chat history for a session.

        Args:
            session_id: Session UUID
            limit: Maximum messages to return

        Returns:
            List of chat messages, oldest first
        """
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, question, answer, source_type, sources, keywords,
                       response_time_ms, created_at
                FROM chat
                WHERE session_id = %s
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (session_id, limit),
            )
            return cur.fetchall()
