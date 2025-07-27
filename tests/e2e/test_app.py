import os

from playwright.sync_api import sync_playwright


def test_homepage():
    """Simple test to check homepage loads"""
    base_url = os.getenv("BASE_URL", "https://food-diary-nginx")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        try:
            page.goto(base_url, timeout=30000)
            title = page.title()
            assert title == "Food Diary Entry"
        finally:
            browser.close()


def test_authentication():
    """Test OAuth authentication flow"""
    base_url = os.getenv("BASE_URL", "https://food-diary-nginx")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        try:
            page.goto(base_url, timeout=30000)

            # Look for login button
            login_button = page.locator("button:has-text('Sign in with GitHub')")
            if login_button.is_visible():
                # Click and wait for navigation
                with page.expect_navigation():
                    login_button.click()

                # Check if we went to OAuth provider or if there was an error
                if "chrome-error" in page.url:
                    raise AssertionError("OAuth redirect failed - check OAuth configuration")

                # Check if we're now authenticated (should see the main app)
                # Look for elements that only appear when authenticated
                new_entry_tab = page.locator("button.nav-tab:has-text('New Entry')")
                history_tab = page.locator("button.nav-tab:has-text('History')")

                if not (new_entry_tab.is_visible() and history_tab.is_visible()):
                    raise AssertionError("Authentication flow did not complete successfully")
            else:
                # If no login button visible, we might already be authenticated
                new_entry_tab = page.locator("button.nav-tab:has-text('New Entry')")
                if not new_entry_tab.is_visible():
                    raise AssertionError("Cannot determine authentication state")

        except Exception as e:
            # Only print debug info on failure
            print(f"Authentication test failed: {e}")
            print(f"Current URL: {page.url}")
            print(f"Page content snippet: {page.content()[:500]}")
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    test_homepage()
    test_authentication()
