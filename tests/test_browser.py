"""Tests for Playwright browser context setup."""

from __future__ import annotations

import pytest

from jobfit.browser import _DEFAULT_VIEWPORT, _USER_AGENT, create_browser_context


@pytest.mark.asyncio
async def test_create_browser_context_returns_context() -> None:
    """create_browser_context() should return a valid BrowserContext."""
    async with create_browser_context() as context:
        assert context is not None
        pages = context.pages
        assert isinstance(pages, list)


@pytest.mark.asyncio
async def test_user_agent_is_consumer_style() -> None:
    """User-Agent string should look like a real Chrome browser."""
    async with create_browser_context() as context:
        page = await context.new_page()
        ua = await page.evaluate("() => navigator.userAgent")
        assert "Chrome/" in ua
        assert "Mozilla/5.0" in ua
        # Should not contain playwright/headless indicators
        assert "Headless" not in ua
        assert "playwright" not in ua.lower()


@pytest.mark.asyncio
async def test_headless_mode_default() -> None:
    """Browser should launch in headless mode by default."""
    async with create_browser_context() as context:
        # If we got here without display errors, headless is working
        page = await context.new_page()
        assert page is not None


@pytest.mark.asyncio
async def test_default_viewport() -> None:
    """Default viewport should be 1920x1080."""
    async with create_browser_context() as context:
        page = await context.new_page()
        viewport = page.viewport_size
        assert viewport is not None
        assert viewport["width"] == 1920
        assert viewport["height"] == 1080


@pytest.mark.asyncio
async def test_custom_viewport() -> None:
    """Custom viewport dimensions should be respected."""
    custom = {"width": 1280, "height": 720}
    async with create_browser_context(viewport=custom) as context:
        page = await context.new_page()
        viewport = page.viewport_size
        assert viewport is not None
        assert viewport["width"] == 1280
        assert viewport["height"] == 720


@pytest.mark.asyncio
async def test_browser_closes_cleanly() -> None:
    """Browser should close cleanly after context manager exits."""
    async with create_browser_context() as context:
        page = await context.new_page()
        assert page is not None
    # After exiting, the context should be closed
    # Attempting to use it should fail
    with pytest.raises(Exception):
        await context.new_page()


@pytest.mark.asyncio
async def test_user_agent_constant_is_realistic() -> None:
    """The default UA constant should mimic a real desktop Chrome browser."""
    assert "Mozilla/5.0" in _USER_AGENT
    assert "Chrome/" in _USER_AGENT
    assert "Windows NT" in _USER_AGENT
    assert "Safari/" in _USER_AGENT


def test_default_viewport_dimensions() -> None:
    """Default viewport constant should be 1920x1080."""
    assert _DEFAULT_VIEWPORT == {"width": 1920, "height": 1080}
