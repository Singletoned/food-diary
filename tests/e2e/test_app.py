# test_app.py

import unittest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


class TestFoodDiaryApp(unittest.TestCase):
    def setUp(self):
        options = webdriver.ChromeOptions()
        self.driver = webdriver.Remote(
            command_executor="http://selenium:4444/wd/hub", options=options
        )
        self.driver.get("http://app:8000")
        # Wait for page to load
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )

    def tearDown(self):
        self.driver.quit()

    def test_homepage_title(self):
        """Test that the homepage has the correct title"""
        page_title = self.driver.title
        self.assertEqual(page_title, "Food Diary Entry")

        # Also check h1 element
        h1_element = self.driver.find_element(By.TAG_NAME, "h1")
        self.assertEqual(h1_element.text, "Food Diary")

    def test_form_elements_present(self):
        """Test that all form elements are present"""
        # Check for note textarea
        note_textarea = self.driver.find_element(By.ID, "note")
        self.assertIsNotNone(note_textarea)

        # Check for photo input
        photo_input = self.driver.find_element(By.ID, "photo")
        self.assertIsNotNone(photo_input)

        # Check for save button
        save_button = self.driver.find_element(By.CSS_SELECTOR, ".save-button")
        self.assertIsNotNone(save_button)

    def test_note_input_functionality(self):
        """Test that note input works"""
        note_textarea = self.driver.find_element(By.ID, "note")
        test_note = "Test food diary entry"
        note_textarea.send_keys(test_note)

        # Verify the text was entered
        self.assertEqual(note_textarea.get_attribute("value"), test_note)

    def test_save_button_disabled_when_empty(self):
        """Test that save button is disabled when no content"""
        save_button = self.driver.find_element(By.CSS_SELECTOR, ".save-button")
        self.assertTrue(save_button.get_attribute("disabled"))

    def test_save_button_enabled_with_note(self):
        """Test that save button becomes enabled when note is entered"""
        note_textarea = self.driver.find_element(By.ID, "note")
        note_textarea.send_keys("Test entry")

        # Wait a moment for Alpine.js to react
        WebDriverWait(self.driver, 5).until(
            lambda driver: not self.driver.find_element(
                By.CSS_SELECTOR, ".save-button"
            ).get_attribute("disabled")
        )

        save_button = self.driver.find_element(By.CSS_SELECTOR, ".save-button")
        self.assertFalse(save_button.get_attribute("disabled"))


if __name__ == "__main__":
    unittest.main()
