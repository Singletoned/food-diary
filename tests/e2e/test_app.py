import base64

from playwright.sync_api import Page, expect

# A tiny 1x1 transparent PNG as a base64 string
# This avoids needing an actual file on disk for the test
TINY_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)
TINY_PNG_BYTES = base64.b64decode(TINY_PNG_BASE64)
    
# App service name in Docker Compose network is 'app', port 8000
BASE_URL = "http://app:8000"
    
    
def test_save_food_entry(page: Page):
    """
    Tests the core functionality:
    - Navigates to the page.
    - Enters a note.
    - Uploads a photo.
    - Clicks "Save".
    - Verifies the alert.
    - Verifies data is saved to IndexedDB.
    - Verifies form fields are cleared.
    """
    page.goto(BASE_URL)

    # Expect a title "to contain" a substring.
    expect(page).to_have_title("Food Diary Entry")

    # Fill the note
    note_textarea = page.locator("#note")
    expect(note_textarea).to_be_visible()
    note_textarea.fill("Test note from Playwright")

    # Handle file input
    photo_input = page.locator("#photo")
    expect(photo_input).to_be_visible()
    photo_input.set_input_files(
        files=[{"name": "test.png", "mimeType": "image/png", "buffer": TINY_PNG_BYTES}],
    )

    # Check for photo preview
    photo_preview = page.locator("img[alt='Photo preview']")
    expect(photo_preview).to_be_visible()
    expect(photo_preview).to_have_attribute(
        "src",
        lambda s: s.startswith("data:image/png;base64,"),
    )

    # Click the save button
    save_button = page.locator("button", has_text="Save Entry")
    expect(save_button).to_be_enabled()

    # Handle the alert that appears after saving
    # We need to set up the listener *before* the action that causes the dialog
    page.once("dialog", lambda dialog: dialog.accept())

    save_button.click()

    # Wait a brief moment to ensure async operations like IndexedDB write can complete.
    # The alert dialog acceptance implies the main part of saveEntry() in Alpine has finished.
    page.wait_for_timeout(500)

    # Verify IndexedDB content
    entries = page.evaluate(
        """
        async () => {
            return new Promise((resolve, reject) => {
                const request = indexedDB.open("foodDiaryDB", 1);
                request.onsuccess = (event) => {
                    const db = event.target.result;
                    if (!db.objectStoreNames.contains("entries")) {
                        // Store might not exist if this is the first run or DB was cleared
                        resolve([]);
                        return;
                    }
                    const transaction = db.transaction(["entries"], "readonly");
                    const store = transaction.objectStore("entries");
                    const getAllRequest = store.getAll();
                    getAllRequest.onsuccess = () => {
                        resolve(getAllRequest.result);
                    };
                    getAllRequest.onerror = (err) => {
                        console.error("Error reading from IndexedDB in test:", err);
                        reject(err.toString());
                    };
                };
                request.onerror = (err) => {
                    console.error("Error opening IndexedDB in test:", err);
                    reject(err.toString());
                };
            });
        }
    """
    )

    assert entries is not None, "Failed to retrieve entries from IndexedDB"
    assert len(entries) > 0, "No entries found in IndexedDB after saving"

    last_entry = entries[-1]
    assert last_entry["text"] == "Test note from Playwright"
    assert last_entry["photo"] is not None
    assert last_entry["photo"].startswith("data:image/png;base64,")
    assert last_entry["synced"] is False  # New entries are not synced

    # Verify fields are cleared after saving
    expect(note_textarea).to_have_value("")
    expect(photo_preview).not_to_be_visible()
    # The file input itself is reset by the application
    expect(photo_input).to_have_value("")
