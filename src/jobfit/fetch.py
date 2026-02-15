"""Page fetching with timeout and error handling."""

from __future__ import annotations

from playwright.async_api import Error as PlaywrightError

from jobfit.browser import create_browser_context
from jobfit.errors import EXIT_NETWORK, print_error

_PAGE_LOAD_TIMEOUT_MS = 30_000


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
    """
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
            if status >= 400:
                print_error(
                    f"HTTP {status} from {url}",
                    detail=f"The server returned status code {status}.",
                    hint="Check that the URL is correct and the page exists.",
                    exit_code=EXIT_NETWORK,
                )

            return await page.content()

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
