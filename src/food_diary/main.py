import os
import sqlite3
from datetime import datetime

import pypugjs
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

# Determine the application directory (e.g., src/food-diary)
APP_DIR = os.path.dirname(os.path.abspath(__file__))
# Determine the project root directory (parent of src)
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir, os.pardir))

TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")
DB_PATH = os.path.join(PROJECT_ROOT, "food_diary.db")

# Ensure the static directory exists, as Starlette expects it
os.makedirs(STATIC_DIR, exist_ok=True)


# Initialize the database
def init_database():
    """Initialize the SQLite database with the entries table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create entries table
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


# Initialize database on startup
init_database()


def render_pug_template(template_name: str, context: dict = None) -> HTMLResponse:
    """
    Renders a Pug template to an HTMLResponse.
    """
    if context is None:
        context = {}

    template_path = os.path.join(TEMPLATES_DIR, template_name)

    # pypugjs.simple_convert expects the Pug source code as a string
    with open(template_path, "r") as f:
        pug_source = f.read()

    # pypugjs compiler options can be passed here if needed
    # For example, to use a specific Jinja2 environment or filters
    # compiler = pypugjs.Compiler(source=pug_source, ...)
    # html = compiler.compile()
    # For simplicity, using simple_convert which uses default compiler settings
    html_content = pypugjs.simple_convert(pug_source)

    return HTMLResponse(html_content)


async def homepage(request):
    """
    Serves the homepage by rendering the index.pug template.
    """
    return render_pug_template("index.pug", {"request": request})


# API endpoints
async def get_entries(request: Request):
    """Get all entries from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, timestamp, text, photo, synced 
        FROM entries 
        ORDER BY timestamp DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    entries = []
    for row in rows:
        entries.append(
            {
                "id": row[0],
                "timestamp": row[1],
                "text": row[2],
                "photo": row[3],
                "synced": bool(row[4]),
            }
        )

    return JSONResponse(entries)


async def create_entry(request: Request):
    """Create a new entry in the database."""
    try:
        data = await request.json()
        timestamp = data.get("timestamp", datetime.now().isoformat())
        text = data.get("text", "")
        photo = data.get("photo")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO entries (timestamp, text, photo, synced)
            VALUES (?, ?, ?, TRUE)
        """,
            (timestamp, text, photo),
        )

        entry_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return JSONResponse(
            {"id": entry_id, "timestamp": timestamp, "text": text, "photo": photo, "synced": True},
            status_code=201,
        )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def update_entry(request: Request):
    """Update an existing entry."""
    try:
        entry_id = request.path_params["entry_id"]
        data = await request.json()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if entry exists
        cursor.execute("SELECT id FROM entries WHERE id = ?", (entry_id,))
        if not cursor.fetchone():
            conn.close()
            return JSONResponse({"error": "Entry not found"}, status_code=404)

        # Update entry
        cursor.execute(
            """
            UPDATE entries 
            SET text = ?, photo = ?, synced = TRUE
            WHERE id = ?
        """,
            (data.get("text", ""), data.get("photo"), entry_id),
        )

        conn.commit()
        conn.close()

        return JSONResponse({"message": "Entry updated successfully"})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def delete_entry(request: Request):
    """Delete an entry from the database."""
    try:
        entry_id = request.path_params["entry_id"]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if entry exists
        cursor.execute("SELECT id FROM entries WHERE id = ?", (entry_id,))
        if not cursor.fetchone():
            conn.close()
            return JSONResponse({"error": "Entry not found"}, status_code=404)

        # Delete entry
        cursor.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        conn.commit()
        conn.close()

        return JSONResponse({"message": "Entry deleted successfully"})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


routes = [
    Route("/", homepage),
    Route("/api/entries", get_entries, methods=["GET"]),
    Route("/api/entries", create_entry, methods=["POST"]),
    Route("/api/entries/{entry_id:int}", update_entry, methods=["PUT"]),
    Route("/api/entries/{entry_id:int}", delete_entry, methods=["DELETE"]),
    Mount("/static", app=StaticFiles(directory=STATIC_DIR), name="static"),
]

app = Starlette(debug=True, routes=routes)
