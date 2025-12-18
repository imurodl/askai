"""Search service for AskAI."""

from typing import Optional, List, Dict, Any
from ..database.db import Database


class SearchService:
    """Service for searching and retrieving questions."""

    def __init__(self):
        self.db = Database()

    def search(self, query: str, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """Search questions by keyword.

        Args:
            query: Search term
            limit: Max results to return
            offset: Pagination offset

        Returns:
            Dict with results, total count, and query
        """
        conn = self.db.connect()
        with conn.cursor() as cur:
            # Search in title, question_text, and answer
            # Using ILIKE for case-insensitive search
            search_pattern = f"%{query}%"

            # Get total count
            cur.execute(
                """
                SELECT COUNT(*) as total
                FROM questions
                WHERE is_fully_scraped = true
                AND (
                    question_title ILIKE %s
                    OR question_text ILIKE %s
                    OR answer ILIKE %s
                )
                """,
                (search_pattern, search_pattern, search_pattern),
            )
            total = cur.fetchone()["total"]

            # Get results
            cur.execute(
                """
                SELECT
                    id,
                    url,
                    question_title as title,
                    category,
                    view_count,
                    LEFT(answer, 150) as answer_preview
                FROM questions
                WHERE is_fully_scraped = true
                AND (
                    question_title ILIKE %s
                    OR question_text ILIKE %s
                    OR answer ILIKE %s
                )
                ORDER BY view_count DESC NULLS LAST, id DESC
                LIMIT %s OFFSET %s
                """,
                (search_pattern, search_pattern, search_pattern, limit, offset),
            )
            results = cur.fetchall()

        return {
            "results": results,
            "total": total,
            "query": query,
            "limit": limit,
            "offset": offset,
        }

    def get_question_by_id(self, question_id: int) -> Optional[Dict[str, Any]]:
        """Get a question by ID with its related questions.

        Args:
            question_id: The question ID

        Returns:
            Question dict with related questions, or None if not found
        """
        conn = self.db.connect()
        with conn.cursor() as cur:
            # Get the main question
            cur.execute(
                """
                SELECT
                    id,
                    url,
                    question_title as title,
                    question_text as question,
                    answer,
                    answer_author as author,
                    category,
                    published_date,
                    view_count
                FROM questions
                WHERE id = %s AND is_fully_scraped = true
                """,
                (question_id,),
            )
            question = cur.fetchone()

            if not question:
                return None

            # Get related questions
            cur.execute(
                """
                SELECT
                    q.id,
                    q.question_title as title,
                    q.url
                FROM question_relationships qr
                JOIN questions q ON q.id = qr.related_question_id
                WHERE qr.question_id = %s
                AND q.is_fully_scraped = true
                ORDER BY qr.position
                LIMIT 10
                """,
                (question_id,),
            )
            related = cur.fetchall()

            result = dict(question)
            result["related_questions"] = related
            return result

    def get_popular(self, limit: int = 10) -> Dict[str, Any]:
        """Get popular questions sorted by view count.

        Args:
            limit: Max results to return

        Returns:
            Dict with results
        """
        conn = self.db.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    url,
                    question_title as title,
                    category,
                    view_count,
                    LEFT(answer, 150) as answer_preview
                FROM questions
                WHERE is_fully_scraped = true
                AND view_count > 0
                ORDER BY view_count DESC
                LIMIT %s
                """,
                (limit,),
            )
            results = cur.fetchall()

        return {"results": results}
