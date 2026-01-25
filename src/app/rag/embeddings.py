"""Parallel embedding generation with multiple API keys."""

import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional, List
from dotenv import load_dotenv
from ..database.db import Database
from .gemini import generate_embedding_with_key

load_dotenv()

# Collect all API keys
API_KEYS = [
    os.getenv("GEMINI_API_KEY"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
    os.getenv("GEMINI_API_KEY_4"),
    os.getenv("GEMINI_API_KEY_5"),
]
API_KEYS = [k for k in API_KEYS if k]  # Filter out None values

# Rate limiting per key (Google allows ~1500 RPM, we use 100 for safety)
REQUESTS_PER_MINUTE = 100
DELAY_BETWEEN_REQUESTS = 60 / REQUESTS_PER_MINUTE  # 0.6 seconds


class EmbeddingWorker:
    """Worker that processes embeddings using one API key."""

    def __init__(self, worker_id: int, api_key: str):
        self.worker_id = worker_id
        self.api_key = api_key
        self.processed = 0
        self.errors = 0
        self.rate_limit_hits = 0
        self.delay = DELAY_BETWEEN_REQUESTS
        self.lock = threading.Lock()

    def process_question(self, question: dict, db_conn) -> bool:
        """Process a single question and store embedding."""
        try:
            # Combine text for embedding
            text_parts = [question["question_title"]]
            if question["question_text"]:
                text_parts.append(question["question_text"])
            if question["answer"]:
                text_parts.append(question["answer"])

            text = "\n".join(text_parts)
            if len(text) > 10000:
                text = text[:10000]

            # Generate embedding
            embedding = generate_embedding_with_key(text, self.api_key)

            # Store in database
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"
            with db_conn.cursor() as cur:
                cur.execute(
                    "UPDATE questions SET embedding = %s::vector WHERE id = %s",
                    (embedding_str, question["id"]),
                )
            db_conn.commit()

            with self.lock:
                self.processed += 1

            time.sleep(self.delay)
            return True

        except Exception as e:
            error_msg = str(e)
            with self.lock:
                self.errors += 1

            if "429" in error_msg or "quota" in error_msg.lower():
                with self.lock:
                    self.rate_limit_hits += 1
                    if self.rate_limit_hits >= 3:
                        self.delay = min(self.delay * 1.5, 5.0)
                print(f"[Worker {self.worker_id}] Rate limited, waiting 60s...")
                time.sleep(60)
            else:
                print(f"[Worker {self.worker_id}] Error on {question['id']}: {error_msg}")
                db_conn.rollback()

            return False


def generate_all_embeddings_parallel(
    start_from_id: Optional[int] = None,
    limit: Optional[int] = None,
):
    """Generate embeddings using all API keys in parallel.

    Args:
        start_from_id: Optional ID to resume from
        limit: Optional limit on total questions to process
    """
    num_workers = len(API_KEYS)
    if num_workers == 0:
        print("No API keys found!")
        return

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
        if limit:
            query += f" LIMIT {limit}"

        cur.execute(query)
        questions = cur.fetchall()

    total = len(questions)
    if total == 0:
        print("No questions to process!")
        db.close()
        return

    print("=" * 60)
    print("Parallel Embedding Generation")
    print("=" * 60)
    print(f"Questions to embed: {total}")
    print(f"API keys: {num_workers}")
    print(f"RPM per key: {REQUESTS_PER_MINUTE}")
    print(f"Total RPM: ~{num_workers * REQUESTS_PER_MINUTE}")
    print(f"Estimated time: {total / (num_workers * REQUESTS_PER_MINUTE) / 60:.1f} hours")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Create workers
    workers = [EmbeddingWorker(i, key) for i, key in enumerate(API_KEYS)]

    # Create separate DB connections for each worker
    worker_connections = [Database().connect() for _ in range(num_workers)]

    # Distribute questions to workers (round-robin)
    question_batches: List[List[dict]] = [[] for _ in range(num_workers)]
    for i, q in enumerate(questions):
        question_batches[i % num_workers].append(q)

    start_time = time.time()
    stop_flag = threading.Event()

    def worker_task(worker: EmbeddingWorker, questions: List[dict], conn):
        for q in questions:
            if stop_flag.is_set():
                break
            worker.process_question(q, conn)

    # Progress monitor
    def progress_monitor():
        while not stop_flag.is_set():
            time.sleep(10)
            total_processed = sum(w.processed for w in workers)
            total_errors = sum(w.errors for w in workers)
            elapsed = time.time() - start_time
            rate = total_processed / elapsed * 60 if elapsed > 0 else 0
            remaining = (total - total_processed) / rate / 60 if rate > 0 else 0
            print(
                f"Progress: {total_processed}/{total} ({100*total_processed/total:.1f}%) | "
                f"Rate: {rate:.0f}/min | "
                f"ETA: {remaining:.1f}h | "
                f"Errors: {total_errors}"
            )

    # Start progress monitor
    monitor_thread = threading.Thread(target=progress_monitor, daemon=True)
    monitor_thread.start()

    # Run workers in parallel
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(worker_task, workers[i], question_batches[i], worker_connections[i])
            for i in range(num_workers)
        ]

        try:
            for future in as_completed(futures):
                future.result()
        except KeyboardInterrupt:
            print("\nStopping...")
            stop_flag.set()

    stop_flag.set()

    # Close worker connections
    for wc in worker_connections:
        wc.close()

    # Final stats
    elapsed = time.time() - start_time
    total_processed = sum(w.processed for w in workers)
    total_errors = sum(w.errors for w in workers)

    print("\n" + "=" * 60)
    print("Session Complete")
    print("=" * 60)
    print(f"Processed: {total_processed}")
    print(f"Errors: {total_errors}")
    print(f"Time: {elapsed/3600:.2f} hours")
    print(f"Actual rate: {total_processed / elapsed * 60:.0f}/min")
    for i, w in enumerate(workers):
        print(f"  Worker {i}: {w.processed} processed, {w.errors} errors")
    print("=" * 60)

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

    print("=" * 50)
    print("Embedding Status")
    print("=" * 50)
    print(f"With embeddings:    {with_emb:,} ({100*with_emb/total:.1f}%)" if total > 0 else "No data")
    print(f"Without embeddings: {without_emb:,} ({100*without_emb/total:.1f}%)" if total > 0 else "")
    print(f"Total:              {total:,}")
    print("=" * 50)

    if without_emb > 0:
        num_keys = len(API_KEYS)
        rpm_total = num_keys * REQUESTS_PER_MINUTE
        hours = without_emb / rpm_total / 60
        print(f"With {num_keys} API keys at {REQUESTS_PER_MINUTE} RPM each:")
        print(f"  Estimated time: {hours:.1f} hours")

    db.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "status":
            check_embedding_status()
        elif sys.argv[1] == "--start-from" and len(sys.argv) > 2:
            start_id = int(sys.argv[2])
            generate_all_embeddings_parallel(start_from_id=start_id)
        elif sys.argv[1] == "--limit" and len(sys.argv) > 2:
            limit = int(sys.argv[2])
            generate_all_embeddings_parallel(limit=limit)
        else:
            print("Usage:")
            print("  python -m app.rag.embeddings              # Run with all keys in parallel")
            print("  python -m app.rag.embeddings status       # Check progress")
            print("  python -m app.rag.embeddings --start-from ID  # Resume from ID")
            print("  python -m app.rag.embeddings --limit N    # Process only N questions")
    else:
        generate_all_embeddings_parallel()
