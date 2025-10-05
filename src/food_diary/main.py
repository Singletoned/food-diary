import logging
import os
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

from .s3_storage import get_storage

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

# AWS configuration
STATIC_BUCKET = os.getenv("STATIC_BUCKET")
CLOUDFRONT_DOMAIN = os.getenv("CLOUDFRONT_DOMAIN")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
API_STAGE_PATH = os.getenv("API_STAGE_PATH", "")

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
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise ValueError(
            "GitHub OAuth requires GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET environment variables. "
            "Please set these in your deployment configuration."
        )
    oauth.register(
        name="github",
        client_id=GITHUB_CLIENT_ID,
        client_secret=GITHUB_CLIENT_SECRET,
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "user:email"},
    )
elif OAUTH_PROVIDER == "mock":
    # Mock OAuth for testing
    mock_oauth_base = os.getenv("MOCK_OAUTH_URL", "http://mock-oauth:8080")
    # For browser redirects, always use localhost so the browser can access it
    mock_oauth_public = os.getenv("MOCK_OAUTH_PUBLIC_URL", "http://localhost:8080")
    oauth.register(
        name="github",  # Keep same name for compatibility
        client_id="mock-client-id",
        client_secret="mock-client-secret",
        # Manually configure endpoints instead of using server metadata
        # to control which URLs are used for browser redirects
        access_token_url=f"{mock_oauth_base}/oauth/token",
        authorize_url=f"{mock_oauth_public}/oauth/authorize",
        api_base_url=f"{mock_oauth_base}/",
        client_kwargs={"scope": "user:email"},
    )
else:
    raise ValueError(f"Unsupported OAuth provider: {OAUTH_PROVIDER}")


# No initialization needed for S3 storage


# Authentication helper functions
def get_current_user(request: Request):
    """Get the current authenticated user from the session."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return get_storage().get_user_by_id(user_id)


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

    # Replace template variables in the pug source for JavaScript injection
    import json

    # Prepare variables for JavaScript section and HTML attributes
    js_replacements = {}
    for key, value in context.items():
        if key == "is_authenticated":
            js_replacements[f"#{{ {key} }}"] = str(value).lower()
            js_replacements[f"#{{{key}}}"] = str(value).lower()
        elif key == "user":
            # Convert user dict to JSON for JavaScript, or null if None
            json_value = json.dumps(value) if value else "null"
            js_replacements[f"#{{ {key} }}"] = json_value
            js_replacements[f"#{{{key}}}"] = json_value
        elif key == "api_stage_path":
            # Pass stage path as string for JavaScript (with quotes)
            js_replacements[f"#{{ {key} }}"] = f'"{value}"'
            # Pass stage path as plain value for HTML attributes (without quotes)
            js_replacements[f"#{{{key}}}"] = str(value)

    # Apply JavaScript replacements
    for pattern, replacement in js_replacements.items():
        pug_source = pug_source.replace(pattern, replacement)

    # Compile Pug with context variables for conditionals
    try:
        html_content = pypugjs.simple_convert(pug_source, **context)
    except Exception:
        # Fallback to simple conversion if context passing fails
        html_content = pypugjs.simple_convert(pug_source)

    return HTMLResponse(html_content)


async def homepage(request):
    """
    Serves the homepage by rendering the index.pug template.
    """
    user = get_current_user(request)
    is_authenticated = user is not None
    context = {
        "request": request,
        "user": user,
        "is_authenticated": is_authenticated,
        "api_stage_path": API_STAGE_PATH,
    }
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

        # Create or update user in S3 storage
        user = get_storage().create_or_update_user(
            github_id=github_user["id"],
            username=github_user["login"],
            name=github_user.get("name"),
            email=github_user.get("email"),
            avatar_url=github_user.get("avatar_url"),
        )
        user_id = user["id"]

        # Store user ID in session
        request.session["user_id"] = user_id

        return RedirectResponse(url=f"{API_STAGE_PATH}/", status_code=302)

    except Exception as e:
        logging.error(f"OAuth callback error: {e}")
        return RedirectResponse(url=f"{API_STAGE_PATH}/?error=auth_failed", status_code=302)


async def logout(request: Request):
    """Log out the user."""
    request.session.clear()
    return RedirectResponse(url=f"{API_STAGE_PATH}/", status_code=302)


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
    """Get all entries from S3 storage for the authenticated user."""
    user_id = request.state.user["id"]
    entries = get_storage().get_entries(user_id)
    return JSONResponse(entries)


@require_auth
async def create_entry(request: Request):
    """Create a new entry in S3 storage for the authenticated user."""
    try:
        user_id = request.state.user["id"]
        data = await request.json()
        timestamp = data.get("timestamp", datetime.now().isoformat())
        event_datetime = data.get("event_datetime", timestamp)
        text = data.get("text", "")
        photo = data.get("photo")

        entry = get_storage().create_entry(
            user_id=user_id,
            timestamp=timestamp,
            event_datetime=event_datetime,
            text=text,
            photo=photo,
        )

        return JSONResponse(entry, status_code=201)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@require_auth
async def update_entry(request: Request):
    """Update an existing entry for the authenticated user."""
    try:
        user_id = request.state.user["id"]
        entry_id = int(request.path_params["entry_id"])
        data = await request.json()

        success = get_storage().update_entry(
            user_id=user_id,
            entry_id=entry_id,
            text=data.get("text"),
            photo=data.get("photo"),
            event_datetime=data.get("event_datetime"),
        )

        if not success:
            return JSONResponse({"error": "Entry not found"}, status_code=404)

        return JSONResponse({"message": "Entry updated successfully"})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@require_auth
async def delete_entry(request: Request):
    """Delete an entry from S3 storage for the authenticated user."""
    try:
        user_id = request.state.user["id"]
        entry_id = int(request.path_params["entry_id"])

        success = get_storage().delete_entry(user_id=user_id, entry_id=entry_id)

        if not success:
            return JSONResponse({"error": "Entry not found"}, status_code=404)

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
]

# Add static file serving - serve files directly from Lambda
routes.append(Mount("/static", app=StaticFiles(directory=STATIC_DIR), name="static"))

# Session middleware for authentication
middleware = [Middleware(SessionMiddleware, secret_key=SECRET_KEY)]

app = Starlette(debug=True, routes=routes, middleware=middleware)
