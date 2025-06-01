def check_homepage_has_title(page):
    """Check that the homepage contains the expected title"""
    page.goto("http://app:8000")
    title_element = page.get_by_role("heading", name="Food Diary Entry")
    if not title_element.is_visible():
        raise AssertionError("Expected title 'Food Diary Entry' not found on page")
    return True
