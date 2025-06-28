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

    # Initialize test database
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            text TEXT,
            photo TEXT,
            synced BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

    yield

    # Clean up test database after each test
    if os.path.exists(TEST_DB_PATH):
        os.unlink(TEST_DB_PATH)


client = TestClient(app)


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


def test_api_get_entries_empty():
    """
    Tests the GET /api/entries endpoint returns empty list initially.
    """
    response = client.get("/api/entries")
    assert response.status_code == 200
    assert response.json() == []


def test_api_create_entry():
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


def test_api_get_entries_with_data():
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


def test_api_delete_entry():
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


def test_api_delete_nonexistent_entry():
    """
    Tests deleting a non-existent entry returns 404.
    """
    response = client.delete("/api/entries/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["error"].lower()
