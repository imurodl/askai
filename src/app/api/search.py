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

    def search_by_keywords(
        self, keywords: List[str], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search using multiple keywords with ILIKE.

        Searches question_title and answer fields for any of the keywords.
        Results are ranked by number of keyword matches.

        Args:
            keywords: List of Cyrillic keywords to search
            limit: Max results to return

        Returns:
            List of matching questions with match_score
        """
        if not keywords:
            return []

        conn = self.db.connect()
        with conn.cursor() as cur:
            # Build ILIKE patterns for each keyword
            patterns = [f"%{kw}%" for kw in keywords]

            # Build dynamic SQL for match scoring
            # Each keyword match in title = 2 points, in answer = 1 point
            score_parts = []
            for i, _ in enumerate(keywords):
                score_parts.append(
                    f"CASE WHEN question_title ILIKE %s THEN 2 ELSE 0 END"
                )
                score_parts.append(
                    f"CASE WHEN answer ILIKE %s THEN 1 ELSE 0 END"
                )
            score_sql = " + ".join(score_parts)

            # Build WHERE clause - match any keyword in title or answer
            where_conditions = []
            for _ in keywords:
                where_conditions.append("question_title ILIKE %s")
                where_conditions.append("answer ILIKE %s")
            where_sql = " OR ".join(where_conditions)

            # Parameters: score patterns + where patterns
            score_params = []
            for p in patterns:
                score_params.extend([p, p])  # title and answer

            where_params = []
            for p in patterns:
                where_params.extend([p, p])  # title and answer

            query = f"""
                SELECT
                    id,
                    question_title as title,
                    question_text as question,
                    answer,
                    category,
                    url,
                    view_count,
                    ({score_sql}) as match_score
                FROM questions
                WHERE is_fully_scraped = true
                AND ({where_sql})
                ORDER BY match_score DESC, view_count DESC NULLS LAST
                LIMIT %s
            """

            all_params = tuple(score_params + where_params + [limit])
            cur.execute(query, all_params)
            results = cur.fetchall()

        return [dict(r) for r in results]

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
