import logging
import os
import sqlite3
from datetime import datetime

import pypugjs
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Determine the application directory (e.g., src/food-diary)
APP_DIR = os.path.dirname(os.path.abspath(__file__))
# Determine the project root directory (parent of src)
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir, os.pardir))

TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")
DB_PATH = os.path.join(PROJECT_ROOT, "food_diary.db")

# Ensure the static directory exists, as Starlette expects it
os.makedirs(STATIC_DIR, exist_ok=True)

# OAuth Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# OAuth Provider Configuration
OAUTH_PROVIDER = os.getenv("OAUTH_PROVIDER", "github")

# Initialize OAuth
oauth = OAuth()

if OAUTH_PROVIDER == "github":
    # Production GitHub OAuth
    oauth.register(
        name="github",
        client_id=GITHUB_CLIENT_ID,
        client_secret=GITHUB_CLIENT_SECRET,
        server_metadata_url="https://api.github.com/.well-known/openid_configuration",
        client_kwargs={"scope": "user:email"},
    )
elif OAUTH_PROVIDER == "mock":
    # Mock OAuth for testing
    mock_oauth_base = os.getenv("MOCK_OAUTH_URL", "http://mock-oauth:8080")
    oauth.register(
        name="github",  # Keep same name for compatibility
        client_id="mock-client-id",
        client_secret="mock-client-secret",
        server_metadata_url=f"{mock_oauth_base}/.well-known/openid_configuration",
        client_kwargs={"scope": "user:email"},
    )
else:
    raise ValueError(f"Unsupported OAuth provider: {OAUTH_PROVIDER}")


# Initialize the database
def init_database():
    """Initialize the SQLite database with the users and entries tables."""
    conn = sqlite3.connect(DB_PATH)
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

    # Create entries table
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

    # Check if user_id column exists, add it if it doesn't (migration)
    cursor.execute("PRAGMA table_info(entries)")
    columns = [row[1] for row in cursor.fetchall()]
    if "user_id" not in columns:
        cursor.execute("ALTER TABLE entries ADD COLUMN user_id INTEGER")
        # Set user_id to 1 for existing entries (temporary for migration)
        cursor.execute("UPDATE entries SET user_id = 1 WHERE user_id IS NULL")

    conn.commit()
    conn.close()


# Initialize database on startup
init_database()


# Authentication helper functions
def get_current_user(request: Request):
    """Get the current authenticated user from the session."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, github_id, username, name, email, avatar_url FROM users WHERE id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "id": row[0],
            "github_id": row[1],
            "username": row[2],
            "name": row[3],
            "email": row[4],
            "avatar_url": row[5],
        }
    return None


def create_or_update_user(github_user_data):
    """Create or update a user based on GitHub user data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if user exists
    cursor.execute("SELECT id FROM users WHERE github_id = ?", (github_user_data["id"],))
    existing_user = cursor.fetchone()

    if existing_user:
        # Update existing user
        cursor.execute(
            """
            UPDATE users SET 
                username = ?, name = ?, email = ?, avatar_url = ?
            WHERE github_id = ?
        """,
            (
                github_user_data["login"],
                github_user_data.get("name"),
                github_user_data.get("email"),
                github_user_data.get("avatar_url"),
                github_user_data["id"],
            ),
        )
        user_id = existing_user[0]
    else:
        # Create new user
        cursor.execute(
            """
            INSERT INTO users (github_id, username, name, email, avatar_url)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                github_user_data["id"],
                github_user_data["login"],
                github_user_data.get("name"),
                github_user_data.get("email"),
                github_user_data.get("avatar_url"),
            ),
        )
        user_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return user_id


def require_auth(func):
    """Decorator to require authentication for a route."""

    async def wrapper(request: Request):
        user = get_current_user(request)
        if not user:
            return JSONResponse({"error": "Authentication required"}, status_code=401)
        request.state.user = user
        return await func(request)

    return wrapper


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
    user = get_current_user(request)
    context = {"request": request, "user": user}
    return render_pug_template("index.pug", context)


# Authentication routes
async def login(request: Request):
    """Initiate GitHub OAuth login."""
    redirect_uri = f"{BASE_URL}/auth/callback"
    return await oauth.github.authorize_redirect(request, redirect_uri)


async def auth_callback(request: Request):
    """Handle GitHub OAuth callback."""
    try:
        token = await oauth.github.authorize_access_token(request)

        # Get user info from GitHub
        if OAUTH_PROVIDER == "mock":
            # For mock OAuth, call the user endpoint directly
            import httpx

            mock_oauth_base = os.getenv("MOCK_OAUTH_URL", "http://mock-oauth:8080")
            headers = {"Authorization": f"Bearer {token['access_token']}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{mock_oauth_base}/user", headers=headers)
                github_user = resp.json()
        else:
            # For real GitHub OAuth
            resp = await oauth.github.get("user", token=token)
            github_user = resp.json()

        # Create or update user in our database
        user_id = create_or_update_user(github_user)

        # Store user ID in session
        request.session["user_id"] = user_id

        return RedirectResponse(url="/", status_code=302)

    except Exception as e:
        logging.error(f"OAuth callback error: {e}")
        return RedirectResponse(url="/?error=auth_failed", status_code=302)


async def logout(request: Request):
    """Log out the user."""
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)


async def user_info(request: Request):
    """Get current user info (API endpoint)."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"authenticated": False})

    return JSONResponse(
        {
            "authenticated": True,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "name": user["name"],
                "avatar_url": user["avatar_url"],
            },
        }
    )


# API endpoints
@require_auth
async def get_entries(request: Request):
    """Get all entries from the database for the authenticated user."""
    user_id = request.state.user["id"]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, timestamp, text, photo, synced 
        FROM entries 
        WHERE user_id = ?
        ORDER BY timestamp DESC
    """,
        (user_id,),
    )

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


@require_auth
async def create_entry(request: Request):
    """Create a new entry in the database for the authenticated user."""
    try:
        user_id = request.state.user["id"]
        data = await request.json()
        timestamp = data.get("timestamp", datetime.now().isoformat())
        text = data.get("text", "")
        photo = data.get("photo")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO entries (user_id, timestamp, text, photo, synced)
            VALUES (?, ?, ?, ?, TRUE)
        """,
            (user_id, timestamp, text, photo),
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


@require_auth
async def update_entry(request: Request):
    """Update an existing entry for the authenticated user."""
    try:
        user_id = request.state.user["id"]
        entry_id = request.path_params["entry_id"]
        data = await request.json()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if entry exists and belongs to user
        cursor.execute("SELECT id FROM entries WHERE id = ? AND user_id = ?", (entry_id, user_id))
        if not cursor.fetchone():
            conn.close()
            return JSONResponse({"error": "Entry not found"}, status_code=404)

        # Update entry
        cursor.execute(
            """
            UPDATE entries 
            SET text = ?, photo = ?, synced = TRUE
            WHERE id = ? AND user_id = ?
        """,
            (data.get("text", ""), data.get("photo"), entry_id, user_id),
        )

        conn.commit()
        conn.close()

        return JSONResponse({"message": "Entry updated successfully"})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@require_auth
async def delete_entry(request: Request):
    """Delete an entry from the database for the authenticated user."""
    try:
        user_id = request.state.user["id"]
        entry_id = request.path_params["entry_id"]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if entry exists and belongs to user
        cursor.execute("SELECT id FROM entries WHERE id = ? AND user_id = ?", (entry_id, user_id))
        if not cursor.fetchone():
            conn.close()
            return JSONResponse({"error": "Entry not found"}, status_code=404)

        # Delete entry
        cursor.execute("DELETE FROM entries WHERE id = ? AND user_id = ?", (entry_id, user_id))
        conn.commit()
        conn.close()

        return JSONResponse({"message": "Entry deleted successfully"})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


routes = [
    Route("/", homepage),
    # Authentication routes
    Route("/auth/login", login),
    Route("/auth/callback", auth_callback),
    Route("/auth/logout", logout),
    Route("/api/user", user_info, methods=["GET"]),
    # Protected API routes
    Route("/api/entries", get_entries, methods=["GET"]),
    Route("/api/entries", create_entry, methods=["POST"]),
    Route("/api/entries/{entry_id:int}", update_entry, methods=["PUT"]),
    Route("/api/entries/{entry_id:int}", delete_entry, methods=["DELETE"]),
    Mount("/static", app=StaticFiles(directory=STATIC_DIR), name="static"),
]

# Session middleware for authentication
middleware = [Middleware(SessionMiddleware, secret_key=SECRET_KEY)]

app = Starlette(debug=True, routes=routes, middleware=middleware)
