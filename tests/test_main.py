from starlette.testclient import TestClient

from food_diary.main import (
    app,
)  # Assuming your app instance is in src/food-diary/main.py

client = TestClient(app)


def test_homepage_loads_successfully():
    """
    Tests if the homepage (/) loads correctly, returns a 200 OK status,
    and contains expected content.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "Hello from Pug!" in response.text
    assert "<title>My Starlette Pug App</title>" in response.text


def test_homepage_includes_app_js():
    """
    Tests if the homepage (/) includes the static/app.js script.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert '<script src="/static/app.js" defer></script>' in response.text
