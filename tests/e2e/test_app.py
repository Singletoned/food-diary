class TestApp:
    """End-to-end tests for the Food Diary application"""

    BASE_URL = "http://app:8000"

    @pytest.fixture(autouse=True)
    def setup(self, playwright):
        self.playwright = playwright
        self.browser = self.playwright.chromium.launch()
        self.context = self.browser.new_context(
            ignore_https_errors=True, bypass_csp=True, java_script_enabled=True
        )
        self.page = self.context.new_page()
        yield
        self.context.close()
        self.browser.close()

    def test_homepage_has_title(self):
        """Test that the homepage loads and contains the expected title"""
        self.page.goto(self.BASE_URL)
        title_element = self.page.get_by_role("heading", name="Food Diary Entry")
        assert title_element.is_visible(), "Expected title 'Food Diary Entry' not found on page"
