"""Web scraper for savollar.islom.uz."""

import os
import time
import logging
from typing import Optional, Set
from urllib.parse import urljoin
import requests
from dotenv import load_dotenv

from .parser import SavollarParser
from ..database.db import Database

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Scraper:
    """Web scraper for savollar.islom.uz Q&A pages."""

    def __init__(self):
        """Initialize scraper with configuration."""
        self.base_url = "https://savollar.islom.uz"
        self.start_url = os.getenv("START_URL", "https://savollar.islom.uz/s/2")
        self.crawl_delay = float(os.getenv("CRAWL_DELAY", "1.0"))
        self.max_pages = int(os.getenv("MAX_PAGES", "0"))  # 0 means unlimited
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.user_agent = os.getenv(
            "USER_AGENT", "DinAI-Bot/1.0 (+https://github.com/imurodl/dinai)"
        )

        self.db = Database()
        self.visited_urls: Set[str] = set()
        self.session_id: Optional[int] = None
        self.pages_scraped = 0

    def _make_request(self, url: str) -> Optional[str]:
        """Make HTTP request with retries.

        Args:
            url: URL to fetch

        Returns:
            HTML content or None if failed
        """
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Fetching: {url} (attempt {attempt + 1}/{self.max_retries})"
                )
                response = requests.get(
                    url, headers=headers, timeout=self.request_timeout
                )
                response.raise_for_status()
                return response.text

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

    def _parse_and_save(self, url: str, html_content: str) -> Optional[str]:
        """Parse HTML content and save to database.

        Args:
            url: The URL of the page
            html_content: HTML content to parse

        Returns:
            Next URL to scrape, or None if no next URL
        """
        parser = SavollarParser(html_content)
        data = parser.extract_all()

        # Log extracted data
        logger.info(f"Extracted: {data['question_title'][:50]}...")
        logger.info(
            f"View count: {data['view_count']}, Similar questions: {len(data['similar_questions'])}"
        )

        # Save to database
        question_id = self.db.insert_question(
            session_id=self.session_id,
            url=url,
            question_title=data["question_title"] or "",
            question_text=data["question_text"],
            answer=data["answer"] or "",
            answer_author=data["answer_author"],
            category=data["category"],
            published_date=data["published_date"],
            view_count=data["view_count"],
        )

        if question_id:
            logger.info(f"Saved question ID: {question_id}")

            # Save related questions
            if data["similar_questions"]:
                related_count = self.db.insert_related_questions(
                    question_id, data["similar_questions"]
                )
                logger.info(f"Saved {related_count} related questions")
        else:
            logger.warning(f"Question already exists: {url}")

        return data["next_url"]

    def scrape(self, start_url: Optional[str] = None):
        """Start scraping from the given URL.

        Args:
            start_url: Starting URL (uses config default if None)
        """
        if start_url:
            self.start_url = start_url

        # Create scrape session
        self.session_id = self.db.create_scrape_session(self.start_url)
        logger.info(f"Started scrape session {self.session_id}")

        current_url = self.start_url

        try:
            while current_url:
                # Check if we've reached max pages
                if self.max_pages > 0 and self.pages_scraped >= self.max_pages:
                    logger.info(f"Reached max pages limit: {self.max_pages}")
                    break

                # Build full URL
                full_url = urljoin(self.base_url, current_url)

                # Check if already visited
                if full_url in self.visited_urls:
                    logger.warning(f"URL already visited: {full_url}")
                    break

                # Check if URL exists in database
                if self.db.question_exists(full_url):
                    logger.info(f"Question already in database: {full_url}")
                    self.visited_urls.add(full_url)
                    # We could still try to get the next URL, but for now we'll stop
                    break

                # Fetch the page
                html_content = self._make_request(full_url)
                if not html_content:
                    logger.error(f"Failed to fetch: {full_url}")
                    break

                # Parse and save
                next_relative_url = self._parse_and_save(full_url, html_content)

                # Mark as visited
                self.visited_urls.add(full_url)
                self.pages_scraped += 1

                # Update session
                self.db.update_scrape_session(
                    session_id=self.session_id,
                    pages_scraped=self.pages_scraped,
                    last_scraped_url=full_url,
                )

                logger.info(f"Progress: {self.pages_scraped} pages scraped")

                # Check if there's a next URL
                if not next_relative_url:
                    logger.info("No more pages to scrape (end of chain)")
                    break

                current_url = next_relative_url

                # Rate limiting - wait before next request
                logger.debug(f"Waiting {self.crawl_delay} seconds...")
                time.sleep(self.crawl_delay)

            # Mark session as completed
            self.db.update_scrape_session(
                session_id=self.session_id, status="completed"
            )
            logger.info(f"Scraping completed! Total pages: {self.pages_scraped}")

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
    """Main entry point for the scraper."""
    scraper = Scraper()
    scraper.scrape()


if __name__ == "__main__":
    main()
