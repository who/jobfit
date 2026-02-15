"""Tests for page fetching with timeout and error handling."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from playwright.async_api import Error as PlaywrightError

from jobfit.fetch import (
    _CAPTCHA_PATTERN,
    _PAGE_LOAD_TIMEOUT_MS,
    _is_login_redirect,
    fetch_page,
)


@pytest.mark.asyncio
async def test_fetch_page_returns_html() -> None:
    """fetch_page() should return full page HTML on success."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.url = "https://example.com"

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
    mock_response.url = "https://example.com"

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
    mock_response.url = "https://example.com"

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


# --- HTTP 403 bot detection hint ---


@pytest.mark.asyncio
async def test_fetch_page_http_403_hints_bot_detection(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """HTTP 403 should hint about bot detection."""
    mock_response = MagicMock()
    mock_response.status = 403

    mock_page = AsyncMock()
    mock_page.goto.return_value = mock_response

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        with pytest.raises(SystemExit) as exc_info:
            await fetch_page("https://example.com/jobs/123")

    assert exc_info.value.code == 4
    captured = capsys.readouterr()
    assert "blocking" in captured.err.lower() or "automated" in captured.err.lower()
    assert "example.com" in captured.err


# --- HTTP 429 rate limiting hint ---


@pytest.mark.asyncio
async def test_fetch_page_http_429_exits_4(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """HTTP 429 should produce exit code 4 with rate limiting hint."""
    mock_response = MagicMock()
    mock_response.status = 429

    mock_page = AsyncMock()
    mock_page.goto.return_value = mock_response

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        with pytest.raises(SystemExit) as exc_info:
            await fetch_page("https://example.com/jobs/456")

    assert exc_info.value.code == 4
    captured = capsys.readouterr()
    assert "429" in captured.err
    assert "rate" in captured.err.lower() or "wait" in captured.err.lower()
    assert "example.com" in captured.err


# --- Login wall detection ---


@pytest.mark.asyncio
async def test_fetch_page_login_redirect_exits_4(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Redirect to login page should produce exit code 4."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.url = "https://example.com/login?redirect=/jobs/123"

    mock_page = AsyncMock()
    mock_page.goto.return_value = mock_response
    mock_page.content.return_value = "<html><body>Please log in</body></html>"

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        with pytest.raises(SystemExit) as exc_info:
            await fetch_page("https://example.com/jobs/123")

    assert exc_info.value.code == 4
    captured = capsys.readouterr()
    assert "login" in captured.err.lower()
    assert "example.com" in captured.err


@pytest.mark.asyncio
async def test_fetch_page_signin_redirect_exits_4(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Redirect to signin page should produce exit code 4."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.url = "https://example.com/signin"

    mock_page = AsyncMock()
    mock_page.goto.return_value = mock_response
    mock_page.content.return_value = "<html><body>Sign in</body></html>"

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        with pytest.raises(SystemExit) as exc_info:
            await fetch_page("https://example.com/jobs/456")

    assert exc_info.value.code == 4
    captured = capsys.readouterr()
    assert "login" in captured.err.lower()


@pytest.mark.asyncio
async def test_fetch_page_no_redirect_not_login_wall() -> None:
    """Same URL should not trigger login wall detection."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.url = "https://example.com/jobs/123"

    mock_page = AsyncMock()
    mock_page.goto.return_value = mock_response
    mock_page.content.return_value = "<html><body>Job posting</body></html>"

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        result = await fetch_page("https://example.com/jobs/123")

    assert result == "<html><body>Job posting</body></html>"


# --- CAPTCHA detection ---


@pytest.mark.asyncio
async def test_fetch_page_captcha_exits_4(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Page with CAPTCHA should produce exit code 4."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.url = "https://example.com/jobs/123"

    mock_page = AsyncMock()
    mock_page.goto.return_value = mock_response
    mock_page.content.return_value = (
        '<html><body><div class="g-recaptcha" data-sitekey="abc"></div></body></html>'
    )

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        with pytest.raises(SystemExit) as exc_info:
            await fetch_page("https://example.com/jobs/123")

    assert exc_info.value.code == 4
    captured = capsys.readouterr()
    assert "captcha" in captured.err.lower()
    assert "example.com" in captured.err


@pytest.mark.asyncio
async def test_fetch_page_hcaptcha_exits_4(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Page with hCaptcha should produce exit code 4."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.url = "https://example.com/jobs/789"

    mock_page = AsyncMock()
    mock_page.goto.return_value = mock_response
    mock_page.content.return_value = (
        '<html><body><div class="h-captcha" data-sitekey="xyz"></div></body></html>'
    )

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        with pytest.raises(SystemExit) as exc_info:
            await fetch_page("https://example.com/jobs/789")

    assert exc_info.value.code == 4
    captured = capsys.readouterr()
    assert "captcha" in captured.err.lower()


@pytest.mark.asyncio
async def test_fetch_page_cloudflare_turnstile_exits_4(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Page with Cloudflare Turnstile should produce exit code 4."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.url = "https://example.com/jobs/101"

    mock_page = AsyncMock()
    mock_page.goto.return_value = mock_response
    mock_page.content.return_value = (
        '<html><body><div class="cf-turnstile"></div></body></html>'
    )

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    with patch("jobfit.fetch.create_browser_context") as mock_browser:
        mock_browser.return_value.__aenter__.return_value = mock_context
        with pytest.raises(SystemExit) as exc_info:
            await fetch_page("https://example.com/jobs/101")

    assert exc_info.value.code == 4
    captured = capsys.readouterr()
    assert "captcha" in captured.err.lower()


# --- _is_login_redirect helper ---


def test_is_login_redirect_same_url() -> None:
    """Same URL should not be a login redirect."""
    assert not _is_login_redirect(
        "https://example.com/jobs/123",
        "https://example.com/jobs/123",
    )


def test_is_login_redirect_to_login() -> None:
    """Redirect to /login should be detected."""
    assert _is_login_redirect(
        "https://example.com/jobs/123",
        "https://example.com/login?next=/jobs/123",
    )


def test_is_login_redirect_to_signin() -> None:
    """Redirect to /signin should be detected."""
    assert _is_login_redirect(
        "https://example.com/jobs/123",
        "https://example.com/signin",
    )


def test_is_login_redirect_to_sso() -> None:
    """Redirect to /sso should be detected."""
    assert _is_login_redirect(
        "https://example.com/jobs/123",
        "https://sso.example.com/sso/authorize",
    )


def test_is_login_redirect_to_oauth() -> None:
    """Redirect to /oauth should be detected."""
    assert _is_login_redirect(
        "https://example.com/jobs/123",
        "https://example.com/oauth/authorize",
    )


def test_is_login_redirect_non_login_redirect() -> None:
    """Redirect to a non-login page should not be detected."""
    assert not _is_login_redirect(
        "https://example.com/jobs/123",
        "https://example.com/jobs/123/details",
    )


# --- CAPTCHA pattern ---


def test_captcha_pattern_matches_recaptcha() -> None:
    """CAPTCHA pattern should match reCAPTCHA."""
    assert _CAPTCHA_PATTERN.search("g-recaptcha")


def test_captcha_pattern_matches_hcaptcha() -> None:
    """CAPTCHA pattern should match hCaptcha."""
    assert _CAPTCHA_PATTERN.search("h-captcha")


def test_captcha_pattern_no_match_normal_page() -> None:
    """CAPTCHA pattern should not match normal page content."""
    assert not _CAPTCHA_PATTERN.search("<html><body>Normal job posting</body></html>")
