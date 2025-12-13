"""HTML parser for savollar.islom.uz website."""

from typing import Optional, List, Dict
from bs4 import BeautifulSoup


class SavollarParser:
    """Parser for extracting Q&A content from savollar.islom.uz pages."""

    def __init__(self, html_content: str):
        """Initialize parser with HTML content.

        Args:
            html_content: Raw HTML string from the webpage
        """
        self.soup = BeautifulSoup(html_content, "html.parser")

    def extract_question_title(self) -> Optional[str]:
        """Extract question title from <h1> tag.

        Returns:
            Question title or None if not found
        """
        h1_tag = self.soup.find("h1")
        return h1_tag.get_text(strip=True) if h1_tag else None

    def extract_question_text(self) -> Optional[str]:
        """Extract question text from div with class 'text_in_question'.

        Returns:
            Question text or None if not found
        """
        question_div = self.soup.find("div", class_="text_in_question")
        return question_div.get_text(strip=True) if question_div else None

    def extract_answer(self) -> Optional[str]:
        """Extract answer from div with class 'answer_in_question'.

        Returns:
            Answer text or None if not found
        """
        answer_div = self.soup.find("div", class_="answer_in_question")
        return answer_div.get_text(strip=True) if answer_div else None

    def extract_answer_author(self) -> Optional[str]:
        """Extract answer author from div with class 'header_answer_inquestion'.

        Returns:
            Author name or None if not found
        """
        author_div = self.soup.find("div", class_="header_answer_inquestion")
        if author_div:
            # Extract text from nested <b> tags
            b_tags = author_div.find_all("b")
            if len(b_tags) >= 2:
                # Get the innermost <b> tag which contains the author name
                author_text = b_tags[1].get_text(strip=True)
                # Remove trailing colon if present
                return author_text.rstrip(":")
        return None

    def extract_category(self) -> Optional[str]:
        """Extract category from breadcrumb navigation.

        Returns:
            Category name or None if not found
        """
        breadcrumb = self.soup.find("nav", {"aria-label": "breadcrumb"})
        if breadcrumb:
            # Find all breadcrumb items
            items = breadcrumb.find_all("li", class_="breadcrumb-item")
            # Get the second-to-last item (the category, not the question itself)
            if len(items) >= 2:
                category_item = items[-2]
                category_link = category_item.find("a")
                if category_link:
                    return category_link.get_text(strip=True)
        return None

    def extract_published_date(self) -> Optional[str]:
        """Extract published date from info_quesiton div.

        Returns:
            Date string (e.g., '16.12.2006') or None if not found
        """
        info_div = self.soup.find("div", class_="info_quesiton")
        if info_div:
            # The format is: "00:00 / 16.12.2006 | <a>...</a> | 13382"
            text = info_div.get_text(strip=True)
            # Split by '|' and get the first part
            parts = text.split("|")
            if parts:
                # Split by '/' and get the date part
                date_parts = parts[0].split("/")
                if len(date_parts) >= 2:
                    return date_parts[1].strip()
        return None

    def extract_next_question_url(self) -> Optional[str]:
        """Extract the next question URL from the navigation.

        Returns:
            Relative URL (e.g., '/s/3') or None if not found
        """
        # Find the div with class 'next_question_b' which contains the next link
        next_div = self.soup.find("div", class_="next_question_b")
        if next_div:
            # Find the parent <a> tag
            parent_link = next_div.find_parent("a")
            if parent_link and parent_link.has_attr("href"):
                return parent_link["href"]
        return None

    def extract_view_count(self) -> Optional[int]:
        """Extract view count from info_quesiton div.

        Returns:
            View count as integer or None if not found
        """
        info_div = self.soup.find("div", class_="info_quesiton")
        if info_div:
            # The format is: "00:00 / 16.12.2006 | <a>...</a> | 13382"
            text = info_div.get_text(strip=True)
            # Split by '|' and get the last part (view count)
            parts = text.split("|")
            if len(parts) >= 3:
                try:
                    view_count_str = parts[2].strip()
                    return int(view_count_str)
                except ValueError:
                    return None
        return None

    def extract_similar_questions(self) -> List[Dict[str, str]]:
        """Extract similar questions from the sidebar.

        Returns:
            List of dictionaries with 'url' and 'title' keys
        """
        similar_questions = []
        
        # Find all divs with class 'similar_question'
        similar_divs = self.soup.find_all("div", class_="similar_question")
        
        for position, div in enumerate(similar_divs, start=1):
            link = div.find("a")
            if link and link.has_attr("href"):
                similar_questions.append({
                    "url": link["href"],
                    "title": link.get_text(strip=True),
                    "position": position
                })
        
        return similar_questions

    def extract_all(self) -> dict:
        """Extract all available data from the page.

        Returns:
            Dictionary containing all extracted data
        """
        return {
            "question_title": self.extract_question_title(),
            "question_text": self.extract_question_text(),
            "answer": self.extract_answer(),
            "answer_author": self.extract_answer_author(),
            "category": self.extract_category(),
            "published_date": self.extract_published_date(),
            "view_count": self.extract_view_count(),
            "similar_questions": self.extract_similar_questions(),
            "next_url": self.extract_next_question_url(),
        }
