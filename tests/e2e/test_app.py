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
            print(f"Attempting to load: {base_url}")
            page.goto(base_url, timeout=30000)
            title = page.title()
            print(f"Page title: {title}")
            print(f"Page URL: {page.url}")
            assert title == "Food Diary Entry"
            print("SUCCESS: Homepage loaded!")
        except Exception as e:
            print(f"ERROR: {e}")
            print(f"Current URL: {page.url}")
            raise
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
            print(f"Testing authentication flow at: {base_url}")
            page.goto(base_url, timeout=30000)

            # Check if we're on login page (unauthenticated)
            print(f"Current URL: {page.url}")

            # Look for login button
            login_button = page.locator("button:has-text('Sign in with GitHub')")
            if login_button.is_visible():
                print("Found login button, clicking...")

                # Listen for navigation events
                def handle_request(request):
                    print(f"Request: {request.method} {request.url}")

                def handle_response(response):
                    print(f"Response: {response.status} {response.url}")

                page.on("request", handle_request)
                page.on("response", handle_response)

                # Click and wait for navigation
                with page.expect_navigation():
                    login_button.click()

                print(f"After login click, current URL: {page.url}")

                # Check if we went to OAuth provider or if there was an error
                if "oauth/authorize" in page.url:
                    print(f"Redirected to OAuth: {page.url}")

                    # Mock OAuth will automatically redirect back with auth code
                    # Wait for redirect back to app
                    page.wait_for_url(f"{base_url}/**", timeout=10000)
                    print(f"Redirected back to app: {page.url}")
                elif "chrome-error" in page.url:
                    print("ERROR: Got Chrome error page, OAuth redirect failed")
                    raise AssertionError("OAuth redirect failed - check OAuth configuration")
                else:
                    print(f"Unexpected URL after login: {page.url}")

                # Check if we're now authenticated (should see the main app)
                # Look for elements that only appear when authenticated
                new_entry_tab = page.locator("button.nav-tab:has-text('New Entry')")
                history_tab = page.locator("button.nav-tab:has-text('History')")

                if new_entry_tab.is_visible() and history_tab.is_visible():
                    print("SUCCESS: Authentication flow completed - main app visible!")
                else:
                    print("ERROR: Main app not visible after authentication")
                    raise AssertionError("Authentication flow did not complete successfully")
            else:
                # If no login button visible, we might already be authenticated
                new_entry_tab = page.locator("button.nav-tab:has-text('New Entry')")
                if new_entry_tab.is_visible():
                    print("SUCCESS: Already authenticated - main app visible!")
                else:
                    print("ERROR: Neither login screen nor main app is visible")
                    print(f"Page content snippet: {page.content()[:1000]}")
                    raise AssertionError("Cannot determine authentication state")

        except Exception as e:
            print(f"ERROR: {e}")
            print(f"Current URL: {page.url}")
            print(f"Page content snippet: {page.content()[:500]}")
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    test_homepage()
    test_authentication()
