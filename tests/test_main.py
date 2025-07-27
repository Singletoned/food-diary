import os
import sqlite3
import tempfile

import pytest
from starlette.testclient import TestClient

from food_diary.main import (
    app,
)  # Assuming your app instance is in src/food-diary/main.py

# Use a test database
TEST_DB_PATH = tempfile.mktemp(suffix=".db")


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Set up a clean test database for each test."""
    # Patch the DB_PATH to use test database
    monkeypatch.setattr("food_diary.main.DB_PATH", TEST_DB_PATH)

    # Initialize test database with full schema
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            github_id INTEGER UNIQUE NOT NULL,
            username TEXT NOT NULL,
            name TEXT,
            email TEXT,
            avatar_url TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create entries table with user_id
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            text TEXT,
            photo TEXT,
            synced BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Create a test user
    cursor.execute("""
        INSERT INTO users (github_id, username, name, email)
        VALUES (12345, 'testuser', 'Test User', 'test@example.com')
    """)
    
    conn.commit()
    conn.close()

    yield

    # Clean up test database after each test
    if os.path.exists(TEST_DB_PATH):
        os.unlink(TEST_DB_PATH)


client = TestClient(app)


@pytest.fixture
def mock_auth(monkeypatch):
    """Mock authentication to return test user."""
    def mock_get_current_user(request):
        return {
            "id": 1,
            "github_id": 12345,
            "username": "testuser",
            "name": "Test User",
            "email": "test@example.com",
            "avatar_url": None,
        }
    
    monkeypatch.setattr("food_diary.main.get_current_user", mock_get_current_user)


def test_homepage_loads_successfully():
    """
    Tests if the homepage (/) loads correctly, returns a 200 OK status,
    and contains expected content.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "Food Diary Entry" in response.text
    assert "<title>Food Diary Entry</title>" in response.text


def test_homepage_includes_app_js():
    """
    Tests if the homepage (/) includes the static/app.js script.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert 'src="/static/app.js"' in response.text


def test_api_get_entries_empty(mock_auth):
    """
    Tests the GET /api/entries endpoint returns empty list initially.
    """
    response = client.get("/api/entries")
    assert response.status_code == 200
    assert response.json() == []


def test_api_create_entry(mock_auth):
    """
    Tests creating a new entry via POST /api/entries.
    """
    entry_data = {"timestamp": "2023-12-07T12:00:00Z", "text": "Test lunch entry", "photo": None}

    response = client.post("/api/entries", json=entry_data)
    assert response.status_code == 201

    created_entry = response.json()
    assert created_entry["text"] == "Test lunch entry"
    assert created_entry["timestamp"] == "2023-12-07T12:00:00Z"
    assert created_entry["synced"] is True
    assert "id" in created_entry


def test_api_get_entries_with_data(mock_auth):
    """
    Tests the GET /api/entries endpoint returns created entries.
    """
    # First create an entry
    entry_data = {
        "timestamp": "2023-12-07T13:00:00Z",
        "text": "Test dinner entry",
        "photo": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/",
    }

    create_response = client.post("/api/entries", json=entry_data)
    assert create_response.status_code == 201

    # Now get all entries
    response = client.get("/api/entries")
    assert response.status_code == 200

    entries = response.json()
    assert len(entries) >= 1

    # Find our created entry
    test_entry = next((e for e in entries if e["text"] == "Test dinner entry"), None)
    assert test_entry is not None
    assert test_entry["photo"] == "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/"


def test_api_delete_entry(mock_auth):
    """
    Tests deleting an entry via DELETE /api/entries/{id}.
    """
    # First create an entry
    entry_data = {"timestamp": "2023-12-07T14:00:00Z", "text": "Entry to be deleted", "photo": None}

    create_response = client.post("/api/entries", json=entry_data)
    assert create_response.status_code == 201
    entry_id = create_response.json()["id"]

    # Delete the entry
    delete_response = client.delete(f"/api/entries/{entry_id}")
    assert delete_response.status_code == 200

    # Verify it's gone
    get_response = client.get("/api/entries")
    entries = get_response.json()
    deleted_entry = next((e for e in entries if e["id"] == entry_id), None)
    assert deleted_entry is None


def test_api_delete_nonexistent_entry(mock_auth):
    """
    Tests deleting a non-existent entry returns 404.
    """
    response = client.delete("/api/entries/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["error"].lower()


def test_homepage_contains_history_view():
    """
    Tests if the homepage contains the history view elements.
    """
    response = client.get("/")
    assert response.status_code == 200
    # Check for history tab
    assert "History" in response.text
    # Check for history container
    assert "history-container" in response.text
    # Check for empty history message
    assert "No entries yet" in response.text


def test_homepage_entry_template_structure():
    """
    Tests if the homepage contains the correct Alpine.js template structure for entries.
    """
    response = client.get("/")
    assert response.status_code == 200
    # Check for Alpine.js entry template
    assert 'x-for="entry in entries"' in response.text
    assert "entry-timestamp" in response.text
    assert "entry-text" in response.text
    assert "entry-photo" in response.text
    assert "delete-button" in response.text


def test_history_functionality_integration(mock_auth):
    """
    Integration test that creates entries via API and verifies they appear in history.
    This tests the full flow from API to frontend data binding.
    """
    # Create multiple entries with different timestamps
    entries_data = [
        {"timestamp": "2023-12-07T09:00:00Z", "text": "Breakfast entry", "photo": None},
        {
            "timestamp": "2023-12-07T12:00:00Z",
            "text": "Lunch entry",
            "photo": "data:image/jpeg;base64,test",
        },
        {"timestamp": "2023-12-07T18:00:00Z", "text": "Dinner entry", "photo": None},
    ]

    created_ids = []
    for entry_data in entries_data:
        response = client.post("/api/entries", json=entry_data)
        assert response.status_code == 201
        created_ids.append(response.json()["id"])

    # Verify entries can be retrieved
    response = client.get("/api/entries")
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) == 3

    # Verify entries have correct data
    texts = [entry["text"] for entry in entries]
    assert "Breakfast entry" in texts
    assert "Lunch entry" in texts
    assert "Dinner entry" in texts


def test_history_entry_deletion(mock_auth):
    """
    Tests that entries can be deleted and are removed from history.
    """
    # Create an entry
    entry_data = {"timestamp": "2023-12-07T15:00:00Z", "text": "Entry to delete", "photo": None}
    create_response = client.post("/api/entries", json=entry_data)
    assert create_response.status_code == 201
    entry_id = create_response.json()["id"]

    # Verify entry exists
    get_response = client.get("/api/entries")
    entries = get_response.json()
    assert any(e["id"] == entry_id for e in entries)

    # Delete the entry
    delete_response = client.delete(f"/api/entries/{entry_id}")
    assert delete_response.status_code == 200

    # Verify entry is gone from history
    get_response = client.get("/api/entries")
    entries = get_response.json()
    assert not any(e["id"] == entry_id for e in entries)
