"""Tests for HTML job posting text extraction."""

from __future__ import annotations

import pytest

from jobfit.errors import EXIT_PARSE
from jobfit.extract_job import extract_job_text


class TestExtractJobText:
    """HTML job posting text extraction works correctly."""

    def test_basic_extraction(self) -> None:
        html = "<html><body><p>Software Engineer position available.</p></body></html>"
        result = extract_job_text(html)
        assert "Software Engineer position available" in result

    def test_multiline_structured_html(self) -> None:
        html = """
        <html><body>
            <h1>Senior Developer</h1>
            <p>We are seeking a talented developer.</p>
            <ul>
                <li>5+ years experience</li>
                <li>Python expertise</li>
            </ul>
        </body></html>
        """
        result = extract_job_text(html)
        assert "Senior Developer" in result
        assert "We are seeking a talented developer" in result
        assert "5+ years experience" in result
        assert "Python expertise" in result

    def test_navigation_boilerplate_stripping(self) -> None:
        html = """
        <html>
            <nav>Home | About | Contact</nav>
            <header>Company Logo</header>
            <body>
                <p>Data Scientist role in research team.</p>
            </body>
            <aside>Related Jobs</aside>
            <footer>Copyright 2026</footer>
        </html>
        """
        result = extract_job_text(html)
        assert "Data Scientist role in research team" in result
        assert "Home | About | Contact" not in result
        assert "Company Logo" not in result
        assert "Related Jobs" not in result
        assert "Copyright 2026" not in result

    def test_script_style_removal(self) -> None:
        html = """
        <html>
            <head>
                <style>body { color: blue; }</style>
                <script>console.log('tracking');</script>
            </head>
            <body>
                <p>Backend Engineer needed.</p>
                <script>trackUser();</script>
            </body>
        </html>
        """
        result = extract_job_text(html)
        assert "Backend Engineer needed" in result
        assert "color: blue" not in result
        assert "console.log" not in result
        assert "trackUser" not in result

    def test_empty_html(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            extract_job_text("")
        assert exc_info.value.code == EXIT_PARSE

    def test_only_script_tags(self) -> None:
        html = """
        <html>
            <head><script>var x = 1;</script></head>
            <body><script>alert('hello');</script></body>
        </html>
        """
        with pytest.raises(SystemExit) as exc_info:
            extract_job_text(html)
        assert exc_info.value.code == EXIT_PARSE

    def test_main_content_detection(self) -> None:
        html = """
        <html>
            <nav>Skip to content</nav>
            <div class="sidebar">Advertisements here</div>
            <main>
                <h1>Product Manager</h1>
                <p>Lead our product strategy and roadmap.</p>
            </main>
            <footer>Legal disclaimers and links</footer>
        </html>
        """
        result = extract_job_text(html)
        assert "Product Manager" in result
        assert "Lead our product strategy and roadmap" in result
        assert "Advertisements here" not in result
        assert "Legal disclaimers" not in result

    def test_list_formatting(self) -> None:
        html = """
        <html><body>
            <h2>Requirements</h2>
            <ul>
                <li>Bachelor's degree</li>
                <li>Strong communication skills</li>
            </ul>
            <h2>Responsibilities</h2>
            <ol>
                <li>Design systems</li>
                <li>Review code</li>
            </ol>
        </body></html>
        """
        result = extract_job_text(html)
        assert "Requirements" in result
        assert "Bachelor's degree" in result
        assert "Strong communication skills" in result
        assert "Responsibilities" in result
        assert "Design systems" in result
        assert "Review code" in result

    def test_heading_preservation(self) -> None:
        html = """
        <html><body>
            <h1>Job Title</h1>
            <h2>About the Role</h2>
            <p>Description here.</p>
            <h3>Qualifications</h3>
            <h4>Required Skills</h4>
            <h5>Preferred Skills</h5>
            <h6>Additional Info</h6>
        </body></html>
        """
        result = extract_job_text(html)
        assert "Job Title" in result
        assert "About the Role" in result
        assert "Description here" in result
        assert "Qualifications" in result
        assert "Required Skills" in result
        assert "Preferred Skills" in result
        assert "Additional Info" in result
        # Verify headings create structure (should have line breaks)
        assert "\n" in result

    def test_return_type(self) -> None:
        html = "<html><body><p>DevOps Engineer position.</p></body></html>"
        result = extract_job_text(html)
        assert isinstance(result, str)

    def test_word_count_availability(self) -> None:
        html = """
        <html><body>
            <h1>Full Stack Developer</h1>
            <p>Join our engineering team to build innovative web applications.</p>
        </body></html>
        """
        result = extract_job_text(html)
        words = result.split()
        assert len(words) > 0
        assert "Full" in words or "Stack" in words or "Developer" in words

    def test_heavy_boilerplate(self) -> None:
        html = """
        <html>
            <head><title>Jobs - Company Site</title></head>
            <nav>
                <a href="/">Home</a>
                <a href="/jobs">Jobs</a>
                <a href="/about">About</a>
            </nav>
            <div class="cookie-banner">
                We use cookies. Accept or decline.
            </div>
            <div class="sidebar">
                <h3>Popular Jobs</h3>
                <ul><li>Job 1</li><li>Job 2</li></ul>
            </div>
            <article>
                <h1>Machine Learning Engineer</h1>
                <p>Build and deploy ML models at scale.</p>
                <h2>Requirements</h2>
                <ul>
                    <li>PhD or Master's in CS</li>
                    <li>Experience with PyTorch</li>
                </ul>
            </article>
            <footer>
                <div>Terms of Service | Privacy Policy</div>
                <div>© 2026 Company Inc. All rights reserved.</div>
            </footer>
        </html>
        """
        result = extract_job_text(html)
        # Job content should be present
        assert "Machine Learning Engineer" in result
        assert "Build and deploy ML models at scale" in result
        assert "Requirements" in result
        assert "PhD or Master's in CS" in result
        assert "Experience with PyTorch" in result
        # Boilerplate should be removed
        assert "We use cookies" not in result
        assert "Popular Jobs" not in result
        assert "Terms of Service" not in result
        assert "All rights reserved" not in result
