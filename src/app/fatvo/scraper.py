"""API scraper for fatvo.uz (newfatvo.saidoffgroup.uz)."""

import os
import time
import logging
from typing import Optional, Dict, Any
import requests
from dotenv import load_dotenv

from ..database.db import Database

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FatvoScraper:
    """API scraper for fatvo.uz Q&A content."""

    def __init__(self):
        """Initialize scraper with configuration."""
        self.base_url = "https://newfatvo.saidoffgroup.uz/api/collections/question_answers/records"
        self.categories_url = "https://newfatvo.saidoffgroup.uz/api/collections/question_categories/records"

        # Configuration from environment
        self.per_page = int(os.getenv("FATVO_PER_PAGE", "100"))
        self.crawl_delay = float(os.getenv("FATVO_CRAWL_DELAY", "0.5"))
        self.request_timeout = int(os.getenv("FATVO_REQUEST_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("FATVO_MAX_RETRIES", "3"))

        self.db = Database()
        self.session_id: Optional[int] = None
        self.questions_scraped = 0

    def _get_resume_point(self) -> tuple[Optional[int], int]:
        """Check for incomplete sessions and determine resume point.

        Returns:
            Tuple of (session_id, last_page):
            - If resuming: (existing_session_id, last_page_number)
            - If starting fresh: (None, 0)
        """
        incomplete_session = self.db.get_last_incomplete_session()

        if not incomplete_session:
            logger.info("No incomplete session found, starting fresh")
            return (None, 0)

        # Check if this is a fatvo session
        start_url = incomplete_session["start_url"]
        if "fatvo" not in start_url.lower():
            logger.info("Found incomplete session but not for fatvo, starting fresh")
            return (None, 0)

        session_id = incomplete_session["id"]
        last_page = self.db.get_fatvo_last_page(session_id)
        pages_scraped = incomplete_session["pages_scraped"] or 0

        logger.info(
            f"Found incomplete fatvo session {session_id}, last page: {last_page}, "
            f"pages scraped: {pages_scraped}"
        )

        return (session_id, last_page)

    def _make_request(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
        """Make HTTP request with retries.

        Args:
            url: URL to fetch
            params: Query parameters

        Returns:
            JSON response or None if failed
        """
        headers = {
            "User-Agent": "AskAI-Bot/1.0 (+https://github.com/imurodl/askai)",
            "Accept": "application/json",
        }

        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"Fetching: {url} (attempt {attempt + 1}/{self.max_retries})"
                )
                response = requests.get(
                    url, params=params, headers=headers, timeout=self.request_timeout
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout for {url}, attempt {attempt + 1}")
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff

            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error for {url}: {e}")
                if response.status_code == 404:
                    return None  # Don't retry 404s
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error for {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)

        return None

    def _scrape_categories(self) -> int:
        """Fetch and save all categories.

        Returns:
            Number of categories saved
        """
        logger.info("Fetching categories...")

        params = {
            "page": 1,
            "perPage": 500,
            "skipTotal": 1,
            "sort": "-created",
            "fields": "id,name,name_cyr,created,updated"
        }

        data = self._make_request(self.categories_url, params)
        if not data or "items" not in data:
            logger.error("Failed to fetch categories")
            return 0

        categories = data["items"]
        saved_count = 0

        for cat in categories:
            cat_id = cat.get("id")
            if not cat_id:
                logger.warning("Skipping category without ID")
                continue

            # Check if already exists
            if self.db.fatvo_category_exists(cat_id):
                logger.debug(f"Category exists: {cat_id}")
                continue

            # Insert category
            result = self.db.insert_fatvo_category(
                category_id=cat_id,
                name_cyr=cat.get("name_cyr") or cat.get("name"),
                name_lat=cat.get("name"),
                created=cat.get("created"),
                updated=cat.get("updated"),
            )

            if result:
                saved_count += 1
                logger.debug(f"Saved category: {cat.get('name_cyr') or cat.get('name')}")

        logger.info(f"Saved {saved_count} categories (out of {len(categories)} total)")
        return saved_count

    def _save_question(self, question: Dict[str, Any]) -> bool:
        """Save a single question to database.

        Args:
            question: Question data from API

        Returns:
            True if saved successfully, False otherwise
        """
        # Validate required fields
        question_id = question.get("id")
        if not question_id:
            logger.warning("Skipping question without ID")
            return False

        # Check if already exists
        if self.db.fatvo_question_exists(question_id):
            logger.debug(f"Question exists: {question_id}")
            return False

        # Map API response to database fields
        # Convert empty string category_id to None to satisfy foreign key constraint
        category_id = question.get("category")
        if category_id == "":
            category_id = None

        result = self.db.insert_fatvo_question(
            question_id=question_id,
            session_id=self.session_id,
            qid=question.get("qid"),
            category_id=category_id,
            title_cyr=question.get("titleCyr"),
            title_lat=question.get("titleLat"),
            question_cyr=question.get("questionCyr"),
            question_lat=question.get("questionLat"),
            answer_cyr=question.get("answerCyr"),
            answer_lat=question.get("answerLat"),
            answered_by=question.get("answeredBy"),
            # Handle API typo: "asweredTime" instead of "answeredTime"
            answered_time=question.get("asweredTime") or question.get("answeredTime"),
            status=question.get("status"),
            scope=question.get("scope"),
            views=question.get("views", 0),
            created=question.get("created"),
            updated=question.get("updated"),
        )

        if result:
            title = question.get("titleCyr") or question.get("titleLat") or "No title"
            logger.debug(f"Saved question {question_id}: {title[:50]}...")
            return True

        return False

    def _scrape_questions_page(self, page: int) -> Optional[Dict]:
        """Fetch one page of questions.

        Args:
            page: Page number (1-indexed)

        Returns:
            API response with items, or None if failed
        """
        params = {
            "page": page,
            "perPage": self.per_page,
        }

        data = self._make_request(self.base_url, params)
        if not data:
            logger.error(f"Failed to fetch page {page}")
            return None

        return data

    def scrape(self):
        """Start scraping from the API."""
        # Check for incomplete sessions and determine resume point
        resume_session_id, resume_page = self._get_resume_point()

        if resume_session_id:
            # Resume existing session
            self.session_id = resume_session_id
            logger.info(f"Resuming scrape session {self.session_id} from page {resume_page + 1}")

            # Update session status back to running
            self.db.update_scrape_session(session_id=self.session_id, status="running")

            current_page = resume_page + 1  # Resume from next page
        else:
            # Create new scrape session
            self.session_id = self.db.create_scrape_session("fatvo-api")
            logger.info(f"Started new scrape session {self.session_id}")
            current_page = 1

        try:
            # Step 1: Scrape categories (only if starting fresh)
            if current_page == 1:
                categories_saved = self._scrape_categories()
                logger.info(f"Categories saved: {categories_saved}")

            # Step 2: Fetch first page to get total count
            logger.info("Fetching first page to determine total...")
            first_page_data = self._scrape_questions_page(current_page)

            if not first_page_data or "items" not in first_page_data:
                logger.error("Failed to fetch first page")
                self.db.update_scrape_session(
                    session_id=self.session_id,
                    status="failed",
                    errors="Failed to fetch first page"
                )
                return

            total_items = first_page_data.get("totalItems", 0)
            total_pages = first_page_data.get("totalPages", 0)

            logger.info(f"Total questions: {total_items} across {total_pages} pages")

            # Process first page
            saved_count = 0
            for question in first_page_data["items"]:
                if self._save_question(question):
                    saved_count += 1

            self.questions_scraped += saved_count
            logger.info(f"Page {current_page}/{total_pages}: Saved {saved_count} questions")

            # Update session
            self.db.update_scrape_session(
                session_id=self.session_id,
                pages_scraped=current_page,
                last_scraped_url=f"page:{current_page}",
            )

            # Step 3: Paginate through remaining pages
            current_page += 1

            while current_page <= total_pages:
                # Rate limiting
                logger.debug(f"Waiting {self.crawl_delay} seconds...")
                time.sleep(self.crawl_delay)

                # Fetch page
                logger.info(f"Fetching page {current_page}/{total_pages}...")
                page_data = self._scrape_questions_page(current_page)

                if not page_data or "items" not in page_data:
                    logger.warning(f"Failed to fetch page {current_page}, continuing...")
                    current_page += 1
                    continue

                # Save questions from this page
                saved_count = 0
                for question in page_data["items"]:
                    if self._save_question(question):
                        saved_count += 1

                self.questions_scraped += saved_count
                logger.info(f"Page {current_page}/{total_pages}: Saved {saved_count} questions")

                # Update session
                self.db.update_scrape_session(
                    session_id=self.session_id,
                    pages_scraped=current_page,
                    last_scraped_url=f"page:{current_page}",
                )

                # Progress report every 5 pages
                if current_page % 5 == 0:
                    percentage = (current_page / total_pages) * 100
                    logger.info(
                        f"Progress: {self.questions_scraped} questions scraped "
                        f"({percentage:.1f}% complete)"
                    )

                current_page += 1

            # Mark session as completed
            self.db.update_scrape_session(
                session_id=self.session_id, status="completed"
            )
            logger.info(f"Scraping completed! Total questions: {self.questions_scraped}")

        except KeyboardInterrupt:
            logger.info("Scraping interrupted by user")
            self.db.update_scrape_session(
                session_id=self.session_id,
                status="failed",
                errors="Interrupted by user",
            )

        except Exception as e:
            logger.error(f"Scraping failed with error: {e}", exc_info=True)
            self.db.update_scrape_session(
                session_id=self.session_id, status="failed", errors=str(e)
            )

        finally:
            self.db.close()
            logger.info("Database connection closed")


def main():
    """Main entry point for the fatvo scraper."""
    logger.info("Starting Fatvo.uz scraper...")
    scraper = FatvoScraper()
    scraper.scrape()


if __name__ == "__main__":
    main()
