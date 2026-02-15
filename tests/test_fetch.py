"""Tests for page fetching with timeout and error handling."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from playwright.async_api import Error as PlaywrightError

from jobfit.fetch import _PAGE_LOAD_TIMEOUT_MS, fetch_page


@pytest.mark.asyncio
async def test_fetch_page_returns_html() -> None:
    """fetch_page() should return full page HTML on success."""
    mock_response = MagicMock()
    mock_response.status = 200

    mock_page = AsyncMock()
    mock_page.goto.return_value = mock_response
    mock_page.content.return_value = "<html><body>Hello</body></html>"

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        result = await fetch_page("https://example.com")

    assert result == "<html><body>Hello</body></html>"


@pytest.mark.asyncio
async def test_fetch_page_uses_30s_timeout() -> None:
    """fetch_page() should pass 30s timeout to page.goto()."""
    mock_response = MagicMock()
    mock_response.status = 200

    mock_page = AsyncMock()
    mock_page.goto.return_value = mock_response
    mock_page.content.return_value = "<html></html>"

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        await fetch_page("https://example.com")

    mock_page.goto.assert_called_once_with(
        "https://example.com",
        timeout=_PAGE_LOAD_TIMEOUT_MS,
        wait_until="load",
    )
    assert _PAGE_LOAD_TIMEOUT_MS == 30_000


@pytest.mark.asyncio
async def test_fetch_page_http_404_exits_4() -> None:
    """HTTP 404 should produce exit code 4."""
    mock_response = MagicMock()
    mock_response.status = 404

    mock_page = AsyncMock()
    mock_page.goto.return_value = mock_response

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        with pytest.raises(SystemExit) as exc_info:
            await fetch_page("https://example.com/missing")

    assert exc_info.value.code == 4


@pytest.mark.asyncio
async def test_fetch_page_http_500_exits_4() -> None:
    """HTTP 500 should produce exit code 4."""
    mock_response = MagicMock()
    mock_response.status = 500

    mock_page = AsyncMock()
    mock_page.goto.return_value = mock_response

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        with pytest.raises(SystemExit) as exc_info:
            await fetch_page("https://example.com/error")

    assert exc_info.value.code == 4


@pytest.mark.asyncio
async def test_fetch_page_http_error_message_includes_status(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """HTTP error message should include the status code."""
    mock_response = MagicMock()
    mock_response.status = 403

    mock_page = AsyncMock()
    mock_page.goto.return_value = mock_response

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        with pytest.raises(SystemExit):
            await fetch_page("https://example.com/forbidden")

    captured = capsys.readouterr()
    assert "403" in captured.err
    assert "example.com" in captured.err


@pytest.mark.asyncio
async def test_fetch_page_dns_failure_exits_4(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """DNS resolution failure should produce exit code 4."""
    mock_page = AsyncMock()
    mock_page.goto.side_effect = PlaywrightError(
        "net::ERR_NAME_NOT_RESOLVED at https://nonexistent.invalid"
    )

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        with pytest.raises(SystemExit) as exc_info:
            await fetch_page("https://nonexistent.invalid")

    assert exc_info.value.code == 4
    captured = capsys.readouterr()
    assert "DNS" in captured.err


@pytest.mark.asyncio
async def test_fetch_page_timeout_exits_4(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Connection timeout should produce exit code 4."""
    mock_page = AsyncMock()
    mock_page.goto.side_effect = PlaywrightError("Timeout 30000ms exceeded")

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        with pytest.raises(SystemExit) as exc_info:
            await fetch_page("https://slow.example.com")

    assert exc_info.value.code == 4
    captured = capsys.readouterr()
    assert "timeout" in captured.err


@pytest.mark.asyncio
async def test_fetch_page_ssl_error_exits_4(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """SSL certificate error should produce exit code 4."""
    mock_page = AsyncMock()
    mock_page.goto.side_effect = PlaywrightError("net::ERR_CERT_AUTHORITY_INVALID")

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        with pytest.raises(SystemExit) as exc_info:
            await fetch_page("https://self-signed.example.com")

    assert exc_info.value.code == 4
    captured = capsys.readouterr()
    assert "SSL" in captured.err


@pytest.mark.asyncio
async def test_fetch_page_connection_refused_exits_4(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Connection refused should produce exit code 4."""
    mock_page = AsyncMock()
    mock_page.goto.side_effect = PlaywrightError("net::ERR_CONNECTION_REFUSED")

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        with pytest.raises(SystemExit) as exc_info:
            await fetch_page("https://localhost:9999")

    assert exc_info.value.code == 4
    captured = capsys.readouterr()
    assert "connection" in captured.err


@pytest.mark.asyncio
async def test_fetch_page_no_response_exits_4() -> None:
    """None response from page.goto should produce exit code 4."""
    mock_page = AsyncMock()
    mock_page.goto.return_value = None

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        with pytest.raises(SystemExit) as exc_info:
            await fetch_page("https://example.com")

    assert exc_info.value.code == 4


@pytest.mark.asyncio
async def test_fetch_page_unknown_playwright_error_exits_4(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unknown Playwright errors should produce exit code 4."""
    mock_page = AsyncMock()
    mock_page.goto.side_effect = PlaywrightError("Something unexpected happened")

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        with pytest.raises(SystemExit) as exc_info:
            await fetch_page("https://example.com")

    assert exc_info.value.code == 4
    captured = capsys.readouterr()
    assert "failed to fetch" in captured.err


@pytest.mark.asyncio
async def test_fetch_page_error_includes_url(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Error messages should include the URL that failed."""
    mock_page = AsyncMock()
    mock_page.goto.side_effect = PlaywrightError("net::ERR_NAME_NOT_RESOLVED")

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        with pytest.raises(SystemExit):
            await fetch_page("https://specific-url.example.com")

    captured = capsys.readouterr()
    assert "specific-url.example.com" in captured.err


@pytest.mark.asyncio
async def test_fetch_page_returns_string() -> None:
    """fetch_page() return type should be str."""
    mock_response = MagicMock()
    mock_response.status = 200

    mock_page = AsyncMock()
    mock_page.goto.return_value = mock_response
    mock_page.content.return_value = "<html></html>"

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        result = await fetch_page("https://example.com")

    assert isinstance(result, str)


def test_page_load_timeout_constant() -> None:
    """Timeout constant should be 30 seconds in milliseconds."""
    assert _PAGE_LOAD_TIMEOUT_MS == 30_000
