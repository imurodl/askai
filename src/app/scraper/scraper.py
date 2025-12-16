"""Web scraper for savollar.islom.uz."""

import os
import re
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

    MAX_CONSECUTIVE_FAILURES = 50  # Stop after 50 consecutive failed pages

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
        self.consecutive_failures = 0  # Track consecutive parsing failures

    @staticmethod
    def _clean_text(text: Optional[str]) -> Optional[str]:
        """Remove NULL bytes from text (PostgreSQL doesn't allow them)."""
        if text is None or text == "":
            return None
        return text.replace("\x00", "")

    def _increment_url(self, url: str) -> Optional[str]:
        """Extract question number from URL and increment it.

        Args:
            url: URL like '/s/1261' or 'https://savollar.islom.uz/s/1261'

        Returns:
            Incremented URL like '/s/1262', or None if URL format is invalid
        """
        # Extract the number from URL pattern /s/NUMBER
        match = re.search(r'/s/(\d+)', url)
        if match:
            current_num = int(match.group(1))
            next_num = current_num + 1
            return f"/s/{next_num}"

        logger.warning(f"Could not extract question number from URL: {url}")
        return None

    def _get_resume_point(self) -> tuple[Optional[int], Optional[str], int]:
        """Check for incomplete sessions and determine resume point.

        Returns:
            Tuple of (session_id, start_url, pages_scraped):
            - If resuming: (existing_session_id, next_url, previous_count)
            - If starting fresh: (None, start_url, 0) where start_url continues from highest existing
        """
        incomplete_session = self.db.get_last_incomplete_session()

        if not incomplete_session:
            # No incomplete session - check if we should continue from existing data
            highest_url = self.db.get_highest_question_url()
            if highest_url:
                # Continue from the next URL after the highest existing one
                next_url = self._increment_url(highest_url)
                if next_url:
                    logger.info(f"No incomplete session, continuing from highest URL: {highest_url} -> {next_url}")
                    return (None, next_url, 0)
            logger.info("No incomplete session found, starting fresh")
            return (None, None, 0)

        session_id = incomplete_session["id"]
        last_url = incomplete_session["last_scraped_url"]
        pages_scraped = incomplete_session["pages_scraped"] or 0

        logger.info(
            f"Found incomplete session {session_id}, last URL: {last_url}, "
            f"pages scraped: {pages_scraped}"
        )

        # If no last URL, check if we can continue from highest existing URL
        if not last_url:
            highest_url = self.db.get_highest_question_url()
            if highest_url:
                next_url = self._increment_url(highest_url)
                if next_url:
                    logger.info(f"No last URL in session, continuing from highest URL: {highest_url} -> {next_url}")
                    return (session_id, next_url, pages_scraped)
            logger.info("No last URL in session, will start from configured START_URL")
            return (session_id, None, pages_scraped)

        # Fetch the last scraped page to get the next URL
        try:
            full_url = urljoin(self.base_url, last_url)
            logger.debug(f"Fetching last scraped page to find next URL: {full_url}")
            html_content = self._make_request(full_url)

            if not html_content:
                logger.warning(
                    f"Failed to fetch last URL {full_url}, will start from configured START_URL"
                )
                return (session_id, None, pages_scraped)

            # Parse to get next URL
            parser = SavollarParser(html_content)
            data = parser.extract_all()
            next_url = data.get("next_url")

            if next_url:
                logger.info(f"Resuming from next URL: {next_url}")
                return (session_id, next_url, pages_scraped)
            else:
                logger.info("No next URL found, session was at the end of chain")
                return (session_id, None, pages_scraped)

        except Exception as e:
            logger.error(f"Error getting resume point: {e}", exc_info=True)
            logger.info("Will start from configured START_URL")
            return (session_id, None, pages_scraped)

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
                logger.debug(
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

    def _parse_and_save(self, url: str, html_content: str) -> tuple[Optional[str], bool]:
        """Parse HTML content and save to database.

        Args:
            url: The URL of the page
            html_content: HTML content to parse

        Returns:
            Tuple of (next_url, success):
            - next_url: Next URL to scrape, or None if no next URL
            - success: True if page was successfully parsed and saved, False otherwise
        """
        parser = SavollarParser(html_content)
        data = parser.extract_all()

        # Log extracted data safely (handle None values)
        title = data['question_title'][:50] if data['question_title'] else 'None'
        logger.debug(f"Extracted: {title}...")
        logger.debug(
            f"View count: {data['view_count']}, Similar questions: {len(data['similar_questions'])}"
        )

        # Validate critical fields - skip saving if question_title is missing
        if not data['question_title']:
            logger.warning(
                f"Skipping page {url} - missing question_title (page structure may be invalid)"
            )
            # Still return next_url to continue the chain, but mark as failure
            return (data["next_url"], False)

        # Extract relative URL from full URL (store as /s/123 instead of full URL)
        relative_url = url.replace('https://savollar.islom.uz', '').replace('http://savollar.islom.uz', '')

        # Save to database (clean text fields to remove NULL bytes)
        question_id = self.db.insert_question(
            session_id=self.session_id,
            url=relative_url,
            question_title=self._clean_text(data["question_title"]) or "",
            question_text=self._clean_text(data["question_text"]),
            answer=self._clean_text(data["answer"]) or "",
            answer_author=self._clean_text(data["answer_author"]),
            category=self._clean_text(data["category"]),
            published_date=data["published_date"],
            view_count=data["view_count"],
        )

        if question_id:
            logger.debug(f"Saved question ID: {question_id}")

            # Save related questions
            if data["similar_questions"]:
                related_count = self.db.insert_related_questions(
                    question_id, data["similar_questions"]
                )
                logger.debug(f"Saved {related_count} related questions")
        else:
            logger.debug(f"Question already exists: {url}")

        return (data["next_url"], True)

    def scrape(self, start_url: Optional[str] = None):
        """Start scraping from the given URL.

        Args:
            start_url: Starting URL (uses config default if None)
        """
        if start_url:
            self.start_url = start_url

        # Check for incomplete sessions and determine resume point
        resume_session_id, resume_url, previous_pages = self._get_resume_point()

        if resume_session_id:
            # Resume existing session
            self.session_id = resume_session_id
            self.pages_scraped = previous_pages
            logger.info(
                f"Resuming scrape session {self.session_id} from page {self.pages_scraped}"
            )

            # Update session status back to running
            self.db.update_scrape_session(session_id=self.session_id, status="running")

            # Determine starting URL
            if resume_url:
                current_url = resume_url
            else:
                # No resume URL, start from configured start_url or end
                if previous_pages == 0:
                    current_url = self.start_url
                    logger.info("Starting from configured START_URL")
                else:
                    # Session was completed or at end of chain
                    logger.info("Session was already at the end, marking as completed")
                    self.db.update_scrape_session(
                        session_id=self.session_id, status="completed"
                    )
                    self.db.close()
                    return
        else:
            # Create new scrape session
            # Use resume_url if provided (continuing from existing data), otherwise use start_url
            current_url = resume_url if resume_url else self.start_url
            self.session_id = self.db.create_scrape_session(current_url)
            logger.info(f"Started new scrape session {self.session_id} from {current_url}")

        try:
            while current_url:
                # Check if we've reached max consecutive failures
                if self.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                    logger.error(
                        f"Reached {self.MAX_CONSECUTIVE_FAILURES} consecutive failures, stopping scraper"
                    )
                    break

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

                # Fetch the page (even if it exists, we need the next URL)
                logger.info(f"Scraping: {full_url}")
                html_content = self._make_request(full_url)
                if not html_content:
                    logger.warning(f"Failed to fetch: {full_url}, trying next URL")
                    self.consecutive_failures += 1

                    # Try incremented URL as fallback
                    incremented_url = self._increment_url(current_url)
                    if incremented_url:
                        logger.info(f"Trying incremented URL: {incremented_url}")
                        current_url = incremented_url
                        time.sleep(self.crawl_delay)
                        continue
                    else:
                        logger.error("Could not increment URL, stopping")
                        break

                # Track if this page was successfully processed
                page_success = False

                # Check if URL already exists in database (use relative URL to match stored format)
                relative_url = current_url if current_url.startswith('/') else f"/{current_url}"
                if self.db.question_exists(relative_url):
                    logger.debug(
                        f"Question already in database: {full_url}, extracting next URL"
                    )
                    # Just parse to get next URL, don't save
                    parser = SavollarParser(html_content)
                    data = parser.extract_all()
                    next_relative_url = data.get("next_url")
                    self.visited_urls.add(full_url)
                    page_success = True  # Existing page is still a success
                else:
                    # Parse and save new question
                    next_relative_url, page_success = self._parse_and_save(full_url, html_content)

                    # Mark as visited
                    self.visited_urls.add(full_url)

                    # If successfully parsed, update counters and session
                    if page_success:
                        self.pages_scraped += 1

                        # Update session
                        self.db.update_scrape_session(
                            session_id=self.session_id,
                            pages_scraped=self.pages_scraped,
                            last_scraped_url=full_url,
                        )

                        # Log progress every 50 pages
                        if self.pages_scraped % 50 == 0:
                            logger.info(f"Progress: {self.pages_scraped} pages scraped")

                # Update consecutive failures counter
                if page_success:
                    self.consecutive_failures = 0  # Reset on success
                else:
                    self.consecutive_failures += 1
                    logger.warning(
                        f"Page parsing failed, consecutive failures: {self.consecutive_failures}"
                    )

                # Check if there's a next URL
                if not next_relative_url:
                    # Try incremented URL as fallback
                    incremented_url = self._increment_url(current_url)
                    if incremented_url:
                        logger.info(
                            f"No next URL found, trying incremented URL: {incremented_url}"
                        )
                        current_url = incremented_url
                    else:
                        logger.info("No more pages to scrape (end of chain)")
                        break
                else:
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
