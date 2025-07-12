import pytest
from playwright.sync_api import Page, BrowserContext


@pytest.fixture
def context(browser):
    context = browser.new_context(ignore_https_errors=True)
    yield context
    context.close()


@pytest.fixture
def page(context):
    page = context.new_page()
    yield page
    page.close()


def test_homepage_title(page: Page):
    """Test that the homepage has the correct title"""
    page.goto("https://nginx")
    
    # Check page title
    assert page.title() == "Food Diary Entry"
    
    # Check h1 element
    h1_element = page.locator("h1")
    assert h1_element.text_content() == "Food Diary"


def test_form_elements_present(page: Page):
    """Test that all form elements are present"""
    page.goto("https://nginx")
    
    # Check for note textarea
    note_textarea = page.locator("#note")
    assert note_textarea.is_visible()
    
    # Check for photo input
    photo_input = page.locator("#photo")
    assert photo_input.is_visible()
    
    # Check for save button
    save_button = page.locator(".save-button")
    assert save_button.is_visible()


def test_note_input_functionality(page: Page):
    """Test that note input works"""
    page.goto("https://nginx")
    
    note_textarea = page.locator("#note")
    test_note = "Test food diary entry"
    note_textarea.fill(test_note)
    
    # Verify the text was entered
    assert note_textarea.input_value() == test_note


def test_save_button_disabled_when_empty(page: Page):
    """Test that save button is disabled when no content"""
    page.goto("https://nginx")
    
    save_button = page.locator(".save-button")
    assert save_button.is_disabled()


def test_save_button_enabled_with_note(page: Page):
    """Test that save button becomes enabled when note is entered"""
    page.goto("https://nginx")
    
    note_textarea = page.locator("#note")
    note_textarea.fill("Test entry")
    
    # Wait for Alpine.js to react
    save_button = page.locator(".save-button")
    assert save_button.is_enabled()


def test_navigation_tabs(page: Page):
    """Test that navigation tabs work correctly"""
    page.goto("https://nginx")
    
    # Wait for Alpine.js to initialize
    page.wait_for_function("() => window.Alpine && window.Alpine.version")
    
    # Check that New Entry tab is active by default
    new_entry_tab = page.locator(".nav-tab").filter(has_text="New Entry")
    history_tab = page.locator(".nav-tab").filter(has_text="History")
    
    assert "active" in new_entry_tab.get_attribute("class")
    
    # Click History tab
    history_tab.click()
    
    # Wait for the view to change
    page.wait_for_selector(".view-container:visible", state="attached")
    
    # Check that History tab is now active
    assert "active" in history_tab.get_attribute("class")
    
    # Check that History view is visible  
    page.wait_for_selector("h2:has-text('Entry History')")
    history_heading = page.locator("h2").filter(has_text="Entry History")
    assert history_heading.is_visible()


def test_entry_save_and_display(page: Page):
    """Test saving an entry and viewing it in history"""
    page.goto("https://nginx")
    
    # Wait for Alpine.js to initialize
    page.wait_for_function("() => window.Alpine && window.Alpine.version")
    
    # Fill in a note with meaningful content
    test_note = "Test food diary entry for history"
    note_textarea = page.locator("#note")
    note_textarea.fill(test_note)
    
    # Set up dialog handler to accept any alert
    page.on("dialog", lambda dialog: dialog.accept())
    
    # Click save button
    save_button = page.locator(".save-button")
    save_button.click()
    
    # The app should automatically switch to history view
    # Wait for the history view heading to be visible
    page.wait_for_selector("h2:has-text('Entry History')", timeout=10000)
    
    # Wait a bit for any IndexedDB operations to complete
    page.wait_for_timeout(2000)
    
    # Check if we're successfully on the history view
    history_heading = page.locator("h2").filter(has_text="Entry History")
    assert history_heading.is_visible()
    
    # Verify the entry was saved and displays correctly
    # Check if there are any entries at all
    entries = page.locator(".entry")
    entry_count = entries.count()
    print(f"Found {entry_count} entries")
    assert entry_count > 0, "No entries found in history"
    
    # Debug: Get the Alpine.js data
    entries_data = page.evaluate("""
        () => {
            const component = document.querySelector('[x-data]')?._x_dataStack?.[0];
            return component ? component.entries : [];
        }
    """)
    print(f"Alpine entries data: {entries_data}")
    
    # Check if the entry text is visible
    entry_text = page.locator(".entry-text")
    entry_text_count = entry_text.count()
    print(f"Found {entry_text_count} entry-text elements")
    
    if entry_text_count > 0:
        for i in range(entry_text_count):
            text_elem = entry_text.nth(i)
            visible = text_elem.is_visible()
            content = text_elem.text_content()
            print(f"Entry text {i}: visible={visible}, content='{content}'")
    
    # Try to find a visible entry text
    visible_entry_text = page.locator(".entry-text:visible")
    if visible_entry_text.count() > 0:
        assert visible_entry_text.first.text_content() == test_note
    else:
        # If none are visible, this is still the bug
        assert False, "No entry-text elements are visible"


def test_empty_history_message(page: Page):
    """Test that empty history shows appropriate message"""
    page.goto("https://nginx")
    
    # Go to history tab
    history_tab = page.locator(".nav-tab").filter(has_text="History")
    history_tab.click()
    
    # Check for empty history message
    empty_message = page.locator(".empty-history")
    assert empty_message.is_visible()
    assert "No entries yet" in empty_message.text_content()


def test_sync_controls_present(page: Page):
    """Test that sync controls are present"""
    page.goto("https://nginx")
    
    # Check for sync button
    sync_button = page.locator(".sync-button")
    assert sync_button.is_visible()
    
    # Check for online status
    online_status = page.locator(".online-status")
    assert online_status.is_visible()