# test_app.py
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time

def test_homepage_title():
    # Connect to the standalone Selenium container
    options = webdriver.ChromeOptions()
    driver = webdriver.Remote(
        command_executor='http://selenium:4444/wd/hub',
        options=options
    )
    
    try:
        # Navigate to your app
        driver.get('http://your-app:8000')
        
        # Wait for page to load (optional but recommended)
        WebDriverWait(driver, 10).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
        
        # Get the page title
        page_title = driver.title
        print(f"Page title: {page_title}")
        
        # Check if expected title is present
        expected_title = "My App Title"
        assert expected_title in page_title, f"Expected '{expected_title}' in title, but got '{page_title}'"
        
        # Alternative: Check for title element content
        # If your title is in an <h1> or other element instead of <title>
        # title_element = driver.find_element(By.TAG_NAME, "h1")
        # assert expected_title in title_element.text
        
        print("Title test passed!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        # Take screenshot for debugging
        driver.save_screenshot("/tmp/error_screenshot.png")
        raise
    
    finally:
        # Always close the browser
        driver.quit()

def test_with_javascript_wait():
    """Example showing how to wait for JavaScript-generated content"""
    driver = webdriver.Remote(
        command_executor='http://selenium:4444/wd/hub',
        desired_capabilities=DesiredCapabilities.CHROME
    )
    
    try:
        driver.get('http://your-app:8000')
        
        # Wait for a specific element that JavaScript creates
        wait = WebDriverWait(driver, 10)
        element = wait.until(
            EC.presence_of_element_located((By.ID, "dynamic-content"))
        )
        
        # Now check the title
        assert "Expected Title" in driver.title
        print("JavaScript content loaded and title verified!")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    test_homepage_title()
    test_with_javascript_wait()
