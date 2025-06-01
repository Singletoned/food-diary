from playwright.sync_api import sync_playwright


def check_homepage_has_title(base_url="http://app:8000"):
    """Check that the homepage loads and contains the expected title"""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        try:
            # Load the page
            page.goto(base_url)

            # Wait for title to be visible
            title_element = page.get_by_role("heading", name="Food Diary Entry")
            if not title_element.is_visible():
                raise AssertionError("Expected title 'Food Diary Entry' not found on page")

            # Verify basic page structure
            form = page.locator(".food-diary-form")
            if not form.is_visible():
                raise AssertionError("Food diary form not found")

            return True

        except Exception as e:
            print(f"Test failed: {str(e)}")
            raise
        finally:
            browser.close()
