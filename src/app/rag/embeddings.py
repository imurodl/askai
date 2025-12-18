"""Batch embedding generation script for all questions.

Respects Gemini API free tier limits:
- ~5-10 RPM (requests per minute)
- ~100-250 RPD (requests per day)

For 75k questions at 250 RPD = ~300 days
For 75k questions at 100 RPD = ~750 days

Better approach: Run at ~5 RPM continuously = 300/hour = 7200/day
At 7200/day, 75k questions = ~10 days
"""

import time
from datetime import datetime
from typing import Optional
from ..database.db import Database
from .gemini import generate_embedding


# Rate limiting settings for Gemini free tier
REQUESTS_PER_MINUTE = 5  # Conservative: 5 RPM
DELAY_BETWEEN_REQUESTS = 60 / REQUESTS_PER_MINUTE  # 12 seconds between requests
DAILY_LIMIT = 7000  # Stop after this many per day to be safe


def generate_all_embeddings(
    start_from_id: Optional[int] = None,
    daily_limit: int = DAILY_LIMIT,
    rpm: int = REQUESTS_PER_MINUTE,
):
    """Generate embeddings respecting Gemini API free tier limits.

    Args:
        start_from_id: Optional ID to resume from
        daily_limit: Max requests per day (default 7000)
        rpm: Requests per minute (default 5)
    """
    delay = 60 / rpm
    db = Database()
    conn = db.connect()

    # Get questions without embeddings
    with conn.cursor() as cur:
        query = """
            SELECT id, question_title, question_text, answer
            FROM questions
            WHERE is_fully_scraped = true
            AND embedding IS NULL
        """
        if start_from_id:
            query += f" AND id >= {start_from_id}"
        query += " ORDER BY id"

        cur.execute(query)
        questions = cur.fetchall()

    total = len(questions)
    print(f"=" * 50)
    print(f"Embedding Generation Started")
    print(f"=" * 50)
    print(f"Questions to embed: {total}")
    print(f"Rate limit: {rpm} RPM ({delay:.1f}s delay)")
    print(f"Daily limit: {daily_limit}")
    print(f"Estimated time: {total * delay / 3600:.1f} hours")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 50)

    processed = 0
    errors = 0
    rate_limit_hits = 0
    start_time = time.time()

    for q in questions:
        # Check daily limit
        if processed >= daily_limit:
            print(f"\nDaily limit ({daily_limit}) reached. Run again tomorrow.")
            print(f"Resume with: --start-from {q['id']}")
            break

        try:
            # Combine text for embedding
            text_parts = [q["question_title"]]
            if q["question_text"]:
                text_parts.append(q["question_text"])
            if q["answer"]:
                text_parts.append(q["answer"])

            text = "\n".join(text_parts)

            # Truncate if too long (Gemini has token limits)
            if len(text) > 10000:
                text = text[:10000]

            # Generate embedding
            embedding = generate_embedding(text)

            # Store in database
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE questions SET embedding = %s::vector WHERE id = %s",
                    (embedding_str, q["id"]),
                )
            conn.commit()

            processed += 1

            # Progress update every 50 questions
            if processed % 50 == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed * 60  # per minute
                remaining = (total - processed) * delay / 3600
                print(
                    f"Progress: {processed}/{total} ({100*processed/total:.1f}%) | "
                    f"Rate: {rate:.1f}/min | "
                    f"ETA: {remaining:.1f}h | "
                    f"Errors: {errors}"
                )

            # Rate limiting - wait between requests
            time.sleep(delay)

        except Exception as e:
            error_msg = str(e)
            errors += 1

            # Check if rate limited
            if "429" in error_msg or "quota" in error_msg.lower():
                rate_limit_hits += 1
                print(f"\nRate limited! Waiting 60 seconds... (hit #{rate_limit_hits})")
                time.sleep(60)

                # If hit too many times, increase delay
                if rate_limit_hits >= 3:
                    delay = delay * 1.5
                    print(f"Increasing delay to {delay:.1f}s")
            else:
                print(f"Error on question {q['id']}: {error_msg}")
                conn.rollback()

            # If too many errors, stop
            if errors > 100:
                print("Too many errors, stopping")
                break

    elapsed = time.time() - start_time
    print(f"\n" + "=" * 50)
    print(f"Session Complete")
    print(f"=" * 50)
    print(f"Processed: {processed}")
    print(f"Errors: {errors}")
    print(f"Time: {elapsed/3600:.2f} hours")
    print(f"Remaining: {total - processed}")
    if processed > 0:
        print(f"Last ID processed: {q['id']}")
        print(f"To resume: python -m app.rag.embeddings --start-from {q['id']}")
    print(f"=" * 50)

    db.close()


def check_embedding_status():
    """Check how many questions have embeddings."""
    db = Database()
    conn = db.connect()

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE embedding IS NOT NULL) as with_embedding,
                COUNT(*) FILTER (WHERE embedding IS NULL AND is_fully_scraped = true) as without_embedding,
                COUNT(*) as total
            FROM questions
            WHERE is_fully_scraped = true
            """
        )
        result = cur.fetchone()

    with_emb = result['with_embedding']
    without_emb = result['without_embedding']
    total = with_emb + without_emb

    print(f"=" * 50)
    print(f"Embedding Status")
    print(f"=" * 50)
    print(f"With embeddings:    {with_emb:,} ({100*with_emb/total:.1f}%)")
    print(f"Without embeddings: {without_emb:,} ({100*without_emb/total:.1f}%)")
    print(f"Total:              {total:,}")
    print(f"=" * 50)

    if without_emb > 0:
        # Estimate time remaining
        hours_at_5rpm = without_emb * 12 / 3600
        days = hours_at_5rpm / 24
        print(f"Estimated time to complete: {hours_at_5rpm:.1f} hours ({days:.1f} days)")

    db.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "status":
            check_embedding_status()
        elif sys.argv[1] == "--start-from" and len(sys.argv) > 2:
            start_id = int(sys.argv[2])
            generate_all_embeddings(start_from_id=start_id)
        else:
            print("Usage:")
            print("  python -m app.rag.embeddings          # Start from beginning")
            print("  python -m app.rag.embeddings status   # Check progress")
            print("  python -m app.rag.embeddings --start-from ID  # Resume from ID")
    else:
        generate_all_embeddings()
