"""
Unit tests for Web Page Routes.

Run with: pytest tests/test_pages.py -v
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create test client."""
    from src.web.main import app

    yield TestClient(app, raise_server_exceptions=False)


# =============================================================================
# INDEX PAGE TESTS
# =============================================================================


class TestIndexPage:
    """Tests for the main index page."""

    def test_index_returns_html(self, client: TestClient) -> None:
        """Should return HTML content."""
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_index_contains_title(self, client: TestClient) -> None:
        """Should contain page title."""
        response = client.get("/")

        assert "Scout" in response.text
        assert "Job Application Generator" in response.text

    def test_index_contains_form(self, client: TestClient) -> None:
        """Should contain job posting form."""
        response = client.get("/")

        assert "job-text" in response.text  # textarea id
        assert "submit-btn" in response.text  # button id
        assert "Paste Job Posting" in response.text

    def test_index_contains_progress_section(self, client: TestClient) -> None:
        """Should contain progress display section."""
        response = client.get("/")

        assert "progress-section" in response.text
        assert "progress-bar" in response.text
        assert "Processing job posting" in response.text

    def test_index_contains_result_section(self, client: TestClient) -> None:
        """Should contain results display section."""
        response = client.get("/")

        assert "result-section" in response.text
        assert "download-cv" in response.text
        assert "download-cover" in response.text

    def test_index_contains_toast_container(self, client: TestClient) -> None:
        """Should contain toast notification container."""
        response = client.get("/")

        assert "toast-container" in response.text

    def test_index_contains_javascript(self, client: TestClient) -> None:
        """Should contain client-side JavaScript."""
        response = client.get("/")

        assert "<script>" in response.text
        assert "startProcessing" in response.text
        # Common JS functions moved to external file
        assert '/static/js/common.js' in response.text


# =============================================================================
# INFO ENDPOINT TESTS
# =============================================================================


class TestInfoEndpoint:
    """Tests for the info endpoint."""

    def test_info_returns_json(self, client: TestClient) -> None:
        """Should return JSON response."""
        response = client.get("/info")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_info_contains_app_data(self, client: TestClient) -> None:
        """Should contain application info."""
        response = client.get("/info")
        data = response.json()

        assert data["name"] == "Scout"
        assert data["version"] == "0.1.0"
        assert data["status"] == "ready"
        assert data["docs"] == "/docs"


# =============================================================================
# HEALTH ENDPOINT TESTS
# =============================================================================


class TestHealthEndpoint:
    """Tests for the health endpoint."""

    def test_health_returns_status(self, client: TestClient) -> None:
        """Should return health status (healthy or degraded)."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        # Status depends on service initialization state
        assert data["status"] in ("healthy", "degraded")

    def test_health_contains_services(self, client: TestClient) -> None:
        """Should report service status."""
        response = client.get("/health")
        data = response.json()

        assert "services" in data
        # Verify services are checked (may be "ok" or have error states)
        assert "pipeline" in data["services"]
        assert "job_store" in data["services"]
        assert "notifications" in data["services"]


# =============================================================================
# PAGE SECTIONS TESTS
# =============================================================================


class TestPageSections:
    """Tests for page section visibility defaults."""

    def test_input_section_visible_by_default(self, client: TestClient) -> None:
        """Input section should be visible by default."""
        response = client.get("/")

        # Check input section doesn't have 'hidden' class in HTML
        # The hidden class is applied via JS, not in template
        assert 'id="input-section"' in response.text

    def test_progress_section_hidden_by_default(self, client: TestClient) -> None:
        """Progress section should have hidden class."""
        response = client.get("/")

        assert 'id="progress-section" class="card hidden"' in response.text

    def test_result_section_hidden_by_default(self, client: TestClient) -> None:
        """Result section should have hidden class."""
        response = client.get("/")

        assert 'id="result-section" class="card hidden"' in response.text

    def test_error_section_hidden_by_default(self, client: TestClient) -> None:
        """Error section should have hidden class."""
        response = client.get("/")

        assert 'id="error-section" class="card error-card hidden"' in response.text


# =============================================================================
# CHARACTER COUNT TESTS
# =============================================================================


class TestCharacterCount:
    """Tests for character count display."""

    def test_char_count_element_exists(self, client: TestClient) -> None:
        """Should have character count element."""
        response = client.get("/")

        assert 'id="char-count"' in response.text

    def test_minimum_chars_warning_in_placeholder(self, client: TestClient) -> None:
        """Should mention minimum characters requirement."""
        response = client.get("/")

        # The 100 char minimum is mentioned in JS logic
        assert "100" in response.text


# =============================================================================
# STEP DISPLAY TESTS
# =============================================================================


class TestStepDisplay:
    """Tests for processing steps display."""

    def test_all_steps_present(self, client: TestClient) -> None:
        """Should display all pipeline steps."""
        response = client.get("/")

        # Check step labels
        assert "Processing job posting" in response.text
        assert "Analyzing compatibility" in response.text
        assert "Generating content" in response.text
        assert "Creating PDFs" in response.text

    def test_step_icons_present(self, client: TestClient) -> None:
        """Should have step icons."""
        response = client.get("/")

        assert 'id="step-icon-rinser"' in response.text
        assert 'id="step-icon-analyzer"' in response.text
        assert 'id="step-icon-creator"' in response.text
        assert 'id="step-icon-formatter"' in response.text


# =============================================================================
# DOWNLOAD LINK TESTS
# =============================================================================


class TestDownloadLinks:
    """Tests for download link elements."""

    def test_cv_download_link(self, client: TestClient) -> None:
        """Should have CV download link."""
        response = client.get("/")

        assert 'id="download-cv"' in response.text
        assert "Download CV" in response.text

    def test_cover_letter_download_link(self, client: TestClient) -> None:
        """Should have cover letter download link."""
        response = client.get("/")

        assert 'id="download-cover"' in response.text
        assert "Download Cover Letter" in response.text


# =============================================================================
# RESET FUNCTIONALITY TESTS
# =============================================================================


class TestResetFunctionality:
    """Tests for reset/retry buttons."""

    def test_reset_button_exists(self, client: TestClient) -> None:
        """Should have reset button."""
        response = client.get("/")

        assert 'id="reset-btn"' in response.text
        assert "Process Another Job" in response.text

    def test_retry_button_exists(self, client: TestClient) -> None:
        """Should have retry button."""
        response = client.get("/")

        assert 'id="retry-btn"' in response.text
        assert "Try Again" in response.text


# =============================================================================
# CSS TESTS
# =============================================================================


class TestCSS:
    """Tests for CSS styles in page."""

    def test_page_has_styles(self, client: TestClient) -> None:
        """Should include CSS styles."""
        response = client.get("/")

        assert "<style>" in response.text

    def test_has_button_styles(self, client: TestClient) -> None:
        """Should link to common CSS with button styling."""
        response = client.get("/")

        # Common styles (including .btn-primary) moved to external file
        assert '/static/css/common.css' in response.text

    def test_has_toast_styles(self, client: TestClient) -> None:
        """Should link to common CSS with toast notification styling."""
        response = client.get("/")

        # Toast styles moved to external CSS file
        assert '/static/css/common.css' in response.text
        # Also verify toast container element exists
        assert 'toast-container' in response.text


# =============================================================================
# STATIC FILES TESTS
# =============================================================================


class TestStaticFiles:
    """Tests for static CSS and JS files."""

    def test_common_css_accessible(self, client: TestClient) -> None:
        """Should serve common CSS file."""
        response = client.get("/static/css/common.css")

        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]

    def test_common_css_has_button_styles(self, client: TestClient) -> None:
        """Common CSS should have button styling."""
        response = client.get("/static/css/common.css")

        assert ".btn" in response.text
        assert ".btn-primary" in response.text

    def test_common_css_has_toast_styles(self, client: TestClient) -> None:
        """Common CSS should have toast notification styling."""
        response = client.get("/static/css/common.css")

        assert ".toast" in response.text
        assert ".toast-success" in response.text
        assert ".toast-error" in response.text

    def test_common_js_accessible(self, client: TestClient) -> None:
        """Should serve common JS file."""
        response = client.get("/static/js/common.js")

        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]

    def test_common_js_has_notification_functions(self, client: TestClient) -> None:
        """Common JS should have notification functions."""
        response = client.get("/static/js/common.js")

        assert "fetchNotifications" in response.text
        assert "showToast" in response.text
        assert "startNotificationPolling" in response.text
