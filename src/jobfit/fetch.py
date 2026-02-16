"""Page fetching with timeout and error handling."""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

from playwright.async_api import Error as PlaywrightError

from jobfit.browser import create_browser_context
from jobfit.errors import EXIT_NETWORK, print_error

logger = logging.getLogger("jobfit.fetch")

_PAGE_LOAD_TIMEOUT_MS = 30_000

_LOGIN_PATH_PATTERN = re.compile(
    r"/(login|signin|sign-in|sign_in|auth|sso|cas|oauth|saml)",
    re.IGNORECASE,
)

_CAPTCHA_PATTERN = re.compile(
    r"(captcha|recaptcha|hcaptcha|g-recaptcha|h-captcha|cf-turnstile"
    r"|challenge-platform|challenge-form)",
    re.IGNORECASE,
)


def _is_login_redirect(original_url: str, final_url: str) -> bool:
    """Check if the page redirected to a login/auth page."""
    original_parsed = urlparse(original_url)
    final_parsed = urlparse(final_url)
    same_host = original_parsed.netloc == final_parsed.netloc
    same_path = original_parsed.path == final_parsed.path
    if same_host and same_path:
        return False
    return bool(_LOGIN_PATH_PATTERN.search(final_parsed.path))


async def fetch_page(url: str) -> str:
    """Fetch page content from a URL using Playwright.

    Navigates to the given URL in a headless browser, waits for the page
    to load, and returns the full HTML content.

    Args:
        url: The URL to fetch.

    Returns:
        The full page HTML as a string.

    Raises:
        SystemExit: On network errors (exit code 4) including:
            - DNS resolution failures
            - Connection timeouts
            - HTTP 4xx/5xx responses
            - SSL errors
            - Login wall detection
            - CAPTCHA detection
    """
    logger.debug("Fetching URL: %s (timeout=%dms)", url, _PAGE_LOAD_TIMEOUT_MS)
    try:
        async with create_browser_context() as context:
            page = await context.new_page()
            response = await page.goto(
                url,
                timeout=_PAGE_LOAD_TIMEOUT_MS,
                wait_until="load",
            )

            if response is None:
                print_error(
                    f"no response from {url}",
                    detail="The page did not return a response.",
                    hint="Check that the URL is correct and the server is running.",
                    exit_code=EXIT_NETWORK,
                )
                raise AssertionError("unreachable")

            status = response.status
            final_url = response.url
            logger.debug("Response: status=%d, final_url=%s", status, final_url)
            response_headers = response.headers
            logger.debug("Response headers: %s", dict(response_headers))
            if status == 403:
                print_error(
                    f"HTTP 403 from {url}",
                    detail="The server returned 403 Forbidden.",
                    hint="The site may be blocking automated access. "
                    "Try opening the URL in a browser to verify it works.",
                    exit_code=EXIT_NETWORK,
                )
            elif status == 429:
                print_error(
                    f"HTTP 429 from {url}",
                    detail="The server returned 429 Too Many Requests.",
                    hint="You are being rate-limited. Wait a few minutes "
                    "and try again.",
                    exit_code=EXIT_NETWORK,
                )
            elif status >= 400:
                print_error(
                    f"HTTP {status} from {url}",
                    detail=f"The server returned status code {status}.",
                    hint="Check that the URL is correct and the page exists.",
                    exit_code=EXIT_NETWORK,
                )

            # Detect login wall via redirect
            if _is_login_redirect(url, final_url):
                print_error(
                    f"login wall detected for {url}",
                    detail=f"The page redirected to a login page: {final_url}",
                    hint="This job posting requires authentication. "
                    "Try copying the posting text manually instead.",
                    exit_code=EXIT_NETWORK,
                )

            html = await page.content()
            logger.debug("Page HTML: length=%d chars", len(html))

            # Detect CAPTCHA in page content
            if _CAPTCHA_PATTERN.search(html):
                print_error(
                    f"CAPTCHA detected on {url}",
                    detail="The page contains a CAPTCHA challenge.",
                    hint="The site is requiring human verification. "
                    "Try opening the URL in a browser and copying the "
                    "posting text manually.",
                    exit_code=EXIT_NETWORK,
                )

            return html

    except PlaywrightError as exc:
        message = str(exc).lower()
        if "timeout" in message:
            print_error(
                f"timeout fetching {url}",
                detail="The page took too long to load (30s limit).",
                hint="Check your internet connection or try again later.",
                exit_code=EXIT_NETWORK,
            )
        elif "net::err_name_not_resolved" in message:
            print_error(
                f"DNS resolution failed for {url}",
                detail="The domain name could not be resolved.",
                hint="Check that the URL is spelled correctly.",
                exit_code=EXIT_NETWORK,
            )
        elif "net::err_cert" in message or "ssl" in message:
            print_error(
                f"SSL error for {url}",
                detail="The SSL certificate could not be verified.",
                hint="Check that the site has a valid SSL certificate.",
                exit_code=EXIT_NETWORK,
            )
        elif "net::err_connection" in message:
            print_error(
                f"connection failed for {url}",
                detail="Could not connect to the server.",
                hint="Check that the URL is correct and the server is running.",
                exit_code=EXIT_NETWORK,
            )
        else:
            print_error(
                f"failed to fetch {url}",
                detail=str(exc),
                exit_code=EXIT_NETWORK,
            )

    # Unreachable — print_error calls sys.exit — but satisfies type checker
    raise AssertionError("unreachable")
