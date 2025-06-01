import base64
import unittest

from playwright.sync_api import expect, sync_playwright

# A tiny 1x1 transparent PNG as a base64 string
TINY_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)
TINY_PNG_BYTES = base64.b64decode(TINY_PNG_BASE64)

# App service name in Docker Compose network is 'app', port 8000
BASE_URL = "http://app:8000"


class FoodDiaryE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        # Create a new context and page for each test to ensure isolation
        # ignore_https_errors=True can help with SSL issues if they persist
        self.context = self.browser.new_context(ignore_https_errors=True)
        self.page = self.context.new_page()

    def tearDown(self):
        self.page.close()
        self.context.close()

    def test_save_food_entry(self):
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
        self.page.goto(BASE_URL)

        # Expect a title "to contain" a substring.
        expect(self.page).to_have_title("Food Diary Entry")

        # Fill the note
        note_textarea = self.page.locator("#note")
        expect(note_textarea).to_be_visible()
        note_textarea.fill("Test note from Playwright with nose2")

        # Handle file input
        photo_input = self.page.locator("#photo")
        expect(photo_input).to_be_visible()
        photo_input.set_input_files(
            files=[{"name": "test.png", "mimeType": "image/png", "buffer": TINY_PNG_BYTES}],
        )

        # Check for photo preview
        photo_preview = self.page.locator("img[alt='Photo preview']")
        expect(photo_preview).to_be_visible()
        expect(photo_preview).to_have_attribute(
            "src",
            lambda s: s.startswith("data:image/png;base64,"),
        )

        # Click the save button
        save_button = self.page.locator("button", has_text="Save Entry")
        expect(save_button).to_be_enabled()

        # Handle the alert that appears after saving
        self.page.once("dialog", lambda dialog: dialog.accept())

        save_button.click()

        self.page.wait_for_timeout(500)  # Allow time for async operations

        # Verify IndexedDB content
        entries = self.page.evaluate(
            """
            async () => {
                return new Promise((resolve, reject) => {
                    const request = indexedDB.open("foodDiaryDB", 1);
                    request.onsuccess = (event) => {
                        const db = event.target.result;
                        if (!db.objectStoreNames.contains("entries")) {
                            resolve([]);
                            return;
                        }
                        const transaction = db.transaction(["entries"], "readonly");
                        const store = transaction.objectStore("entries");
                        const getAllRequest = store.getAll();
                        getAllRequest.onsuccess = () => resolve(getAllRequest.result);
                        getAllRequest.onerror = (err) => reject(err.toString());
                    };
                    request.onerror = (err) => reject(err.toString());
                });
            }
        """
        )

        self.assertIsNotNone(entries, "Failed to retrieve entries from IndexedDB")
        self.assertTrue(len(entries) > 0, "No entries found in IndexedDB after saving")

        last_entry = entries[-1]
        self.assertEqual(last_entry["text"], "Test note from Playwright with nose2")
        self.assertIsNotNone(last_entry["photo"])
        self.assertTrue(last_entry["photo"].startswith("data:image/png;base64,"))
        self.assertFalse(last_entry["synced"])  # New entries are not synced

        # Verify fields are cleared after saving
        expect(note_textarea).to_have_value("")
        expect(photo_preview).not_to_be_visible()
        expect(photo_input).to_have_value("")


if __name__ == "__main__":
    unittest.main()
