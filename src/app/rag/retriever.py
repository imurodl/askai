"""Vector similarity search using pgvector."""

from typing import List, Dict, Any, Optional
from ..database.db import Database


class Retriever:
    """Retrieves relevant Q&A using vector similarity search."""

    def __init__(self):
        self.db = Database()

    def search_similar(
        self,
        embedding: List[float],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find similar questions using cosine similarity.

        Args:
            embedding: Query embedding (768 dimensions)
            limit: Number of results to return

        Returns:
            List of similar questions with relevance scores
        """
        conn = self.db.connect()
        with conn.cursor() as cur:
            # Convert embedding to pgvector format
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"

            cur.execute(
                """
                SELECT
                    id,
                    question_title as title,
                    question_text as question,
                    answer,
                    category,
                    url,
                    1 - (embedding <=> %s::vector) as relevance
                FROM questions
                WHERE is_fully_scraped = true
                AND embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding_str, embedding_str, limit),
            )
            results = cur.fetchall()

        return [dict(r) for r in results]

    def get_question_by_id(self, question_id: int) -> Optional[Dict[str, Any]]:
        """Get a question by ID.

        Args:
            question_id: Question ID

        Returns:
            Question dict or None
        """
        conn = self.db.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    question_title as title,
                    question_text as question,
                    answer,
                    category,
                    url
                FROM questions
                WHERE id = %s AND is_fully_scraped = true
                """,
                (question_id,),
            )
            result = cur.fetchone()
            return dict(result) if result else None
