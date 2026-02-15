"""Playwright browser automation with consumer-style User-Agent."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from playwright.async_api import BrowserContext, async_playwright

# Realistic Chrome on Windows desktop User-Agent
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

_DEFAULT_VIEWPORT = {"width": 1920, "height": 1080}


@asynccontextmanager
async def create_browser_context(
    *,
    headless: bool = True,
    user_agent: str = _USER_AGENT,
    viewport: dict[str, int] | None = None,
) -> AsyncIterator[BrowserContext]:
    """Create a Playwright browser context with consumer-style settings.

    Launches headless Chromium with a realistic User-Agent string and
    reasonable viewport defaults. Use as an async context manager to
    ensure the browser is closed cleanly.

    Args:
        headless: Run browser in headless mode. Defaults to True.
        user_agent: User-Agent string. Defaults to a realistic Chrome UA.
        viewport: Browser viewport dimensions. Defaults to 1920x1080.

    Yields:
        A configured BrowserContext ready for page navigation.
    """
    if viewport is None:
        viewport = _DEFAULT_VIEWPORT

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=user_agent,
            viewport=viewport,
        )
        try:
            yield context
        finally:
            await context.close()
            await browser.close()
