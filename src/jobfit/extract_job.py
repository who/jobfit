"""Extract meaningful job posting text from HTML."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from jobfit.errors import EXIT_PARSE, print_error


def extract_job_text(html: str) -> str:
    """Extract meaningful job posting text from HTML.

    Strips navigation, headers, footers, sidebars, scripts, and other
    boilerplate elements. Focuses on extracting the main job description
    content with reasonable formatting preserved.

    Args:
        html: Raw HTML content from a job posting page.

    Returns:
        Clean text suitable for LLM analysis, with paragraphs and lists
        formatted reasonably.

    Raises:
        SystemExit: If HTML is empty or contains no meaningful content (exit code 6).
    """
    if not html or not html.strip():
        print_error(
            "No HTML content to extract",
            exit_code=EXIT_PARSE,
        )

    soup = BeautifulSoup(html, "html.parser")

    # Remove script, style, noscript, svg, iframe tags
    for tag in soup.find_all(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    # Remove navigation elements: nav, header, footer, aside
    for tag in soup.find_all(["nav", "header", "footer", "aside"]):
        tag.decompose()

    # Remove common boilerplate by class/id/role patterns
    boilerplate_patterns = [
        "nav",
        "footer",
        "sidebar",
        "cookie",
        "banner",
        "menu",
        "breadcrumb",
        "ad",
        "advertisement",
        "social",
        "share",
    ]
    for element in list(soup.find_all(True)):
        if not isinstance(element, Tag) or element.decomposed:
            continue

        # Check class attribute
        classes = element.get("class", [])
        if any(
            pattern in cls.lower()
            for cls in classes
            for pattern in boilerplate_patterns
        ):
            element.decompose()
            continue

        # Check id attribute
        element_id = element.get("id", "")
        if any(pattern in element_id.lower() for pattern in boilerplate_patterns):
            element.decompose()
            continue

        # Check role attribute
        role = element.get("role", "")
        if role.lower() in ["navigation", "banner", "complementary"]:
            element.decompose()
            continue

    # Try to find main content area
    main_content = None

    # Try <main> tag
    main_tag = soup.find("main")
    if main_tag:
        main_content = main_tag

    # Try <article> tag
    if not main_content:
        article_tag = soup.find("article")
        if article_tag:
            main_content = article_tag

    # Try role="main"
    if not main_content:
        role_main = soup.find(attrs={"role": "main"})
        if role_main:
            main_content = role_main

    # Try id/class containing job-related keywords
    if not main_content:
        job_keywords = ["job", "description", "posting", "content"]
        for keyword in job_keywords:
            # Try id first
            element = soup.find(id=lambda x: x and keyword in x.lower())
            if element:
                main_content = element
                break
            # Try class
            element = soup.find(class_=lambda x: x and keyword in x.lower())
            if element:
                main_content = element
                break

    # If no main content area found, use the body
    if not main_content:
        main_content = soup.find("body")
        if not main_content:
            main_content = soup

    # Extract text with formatting
    text = _extract_formatted_text(main_content)

    # Validate meaningful content
    text = text.strip()
    if not text:
        print_error(
            "No meaningful content found in HTML",
            detail="The page appears to contain no readable text content.",
            hint="The page may require JavaScript rendering or authentication.",
            exit_code=EXIT_PARSE,
        )

    return text


def _extract_formatted_text(element: Tag | BeautifulSoup) -> str:
    """Extract text from an element with basic formatting preserved.

    Args:
        element: BeautifulSoup element to extract text from.

    Returns:
        Formatted text with paragraphs, lists, and headings.
    """
    # Replace <br> with newlines
    for br in element.find_all("br"):
        br.replace_with("\n")

    # Build text with structure
    parts: list[str] = []

    def process_element(elem: Tag | BeautifulSoup) -> None:
        """Recursively process elements to extract formatted text."""
        if not isinstance(elem, Tag):
            return

        # Headings get newlines around them
        if elem.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            text = elem.get_text(strip=True)
            if text:
                parts.append(f"\n\n{text}\n\n")

        # Paragraphs get double newlines
        elif elem.name == "p":
            text = elem.get_text(strip=True)
            if text:
                parts.append(f"{text}\n\n")

        # List items get prefixed with dash
        elif elem.name == "li":
            text = elem.get_text(strip=True)
            if text:
                parts.append(f"- {text}\n")

        # Recurse into other containers
        elif elem.name in ["div", "section", "ul", "ol", "body", "main", "article"]:
            for child in elem.children:
                if isinstance(child, Tag):
                    process_element(child)

    # Process the main element
    for child in element.children:
        if isinstance(child, Tag):
            process_element(child)

    # If we didn't get any formatted text, fall back to plain text extraction
    if not parts:
        text = element.get_text(separator=" ", strip=True)
    else:
        text = "".join(parts)

    # Collapse excessive whitespace
    # Replace runs of 3+ newlines with exactly 2
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")

    # Collapse multiple spaces
    text = re.sub(r" +", " ", text)

    return text.strip()
