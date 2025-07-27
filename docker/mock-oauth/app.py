import base64
import secrets
import time
from urllib.parse import urlencode

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route

# In-memory storage for mock data
# Updated to match GitHub API format
mock_users = {
    "123": {
        "id": 123,  # GitHub uses numeric IDs
        "login": "testuser",  # GitHub username field
        "name": "Test User",
        "email": "test@example.com",
        "avatar_url": "https://avatars.githubusercontent.com/u/123?v=4",
    },
    "456": {
        "id": 456,
        "login": "adminuser",
        "name": "Admin User",
        "email": "admin@example.com",
        "avatar_url": "https://avatars.githubusercontent.com/u/456?v=4",
    },
}

# Mock authorization codes and tokens
auth_codes = {}
access_tokens = {}


async def authorize_endpoint(request: Request):
    """Mock OAuth authorization endpoint"""
    params = request.query_params

    client_id = params.get("client_id")
    redirect_uri = params.get("redirect_uri")
    state = params.get("state", "")
    scope = params.get("scope", "read")

    if not client_id or not redirect_uri:
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Missing required parameters"},
            status_code=400,
        )

    # Generate mock authorization code
    auth_code = secrets.token_urlsafe(32)

    # Store the auth code with associated data
    auth_codes[auth_code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "user_id": "123",  # Default to first mock user
        "expires_at": time.time() + 600,  # 10 minutes
    }

    # Build redirect URL with authorization code
    query_params = {"code": auth_code}
    if state:
        query_params["state"] = state

    redirect_url = f"{redirect_uri}?{urlencode(query_params)}"
    return RedirectResponse(url=redirect_url)


async def token_endpoint(request: Request):
    """Mock OAuth token endpoint"""
    print(f"Token endpoint called: {request.method} {request.url}")
    print(f"Headers: {dict(request.headers)}")

    form_data = await request.form()
    print(f"Form data: {dict(form_data)}")

    grant_type = form_data.get("grant_type")
    code = form_data.get("code")
    client_id = form_data.get("client_id")
    client_secret = form_data.get("client_secret")
    redirect_uri = form_data.get("redirect_uri")

    # Handle client credentials in Authorization header
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Basic "):
        try:
            encoded_credentials = auth_header[6:]
            decoded = base64.b64decode(encoded_credentials).decode("utf-8")
            client_id, client_secret = decoded.split(":", 1)
        except Exception:
            pass

    if grant_type != "authorization_code":
        return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)

    if not code or code not in auth_codes:
        return JSONResponse(
            {"error": "invalid_grant", "error_description": "Invalid authorization code"},
            status_code=400,
        )

    auth_data = auth_codes[code]

    # Check if code is expired
    if time.time() > auth_data["expires_at"]:
        del auth_codes[code]
        return JSONResponse(
            {"error": "invalid_grant", "error_description": "Authorization code expired"},
            status_code=400,
        )

    # Validate client_id matches
    if client_id != auth_data["client_id"]:
        return JSONResponse({"error": "invalid_client"}, status_code=400)

    # Generate access token
    access_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(32)

    # Store token data
    access_tokens[access_token] = {
        "user_id": auth_data["user_id"],
        "client_id": client_id,
        "scope": auth_data["scope"],
        "expires_at": time.time() + 3600,  # 1 hour
    }

    # Clean up used authorization code
    del auth_codes[code]

    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": refresh_token,
            "scope": auth_data["scope"],
        }
    )


async def user_info_endpoint(request: Request):
    """Mock user info endpoint - GitHub API compatible"""
    auth_header = request.headers.get("authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            {
                "error": "invalid_token",
                "error_description": "Missing or invalid authorization header",
            },
            status_code=401,
        )

    access_token = auth_header[7:]  # Remove "Bearer " prefix

    if access_token not in access_tokens:
        return JSONResponse(
            {"error": "invalid_token", "error_description": "Invalid access token"}, status_code=401
        )

    token_data = access_tokens[access_token]

    # Check if token is expired
    if time.time() > token_data["expires_at"]:
        del access_tokens[access_token]
        return JSONResponse(
            {"error": "invalid_token", "error_description": "Access token expired"}, status_code=401
        )

    user_id = token_data["user_id"]
    user_data = mock_users.get(user_id)

    if not user_data:
        return JSONResponse({"error": "user_not_found"}, status_code=404)

    return JSONResponse(user_data)


async def openid_configuration(request: Request):
    """Mock OpenID Connect discovery endpoint"""
    # Use Docker network hostname instead of localhost for internal communication
    base_url = "http://mock-oauth:8080"

    return JSONResponse(
        {
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/oauth/authorize",
            "token_endpoint": f"{base_url}/oauth/token",
            "userinfo_endpoint": f"{base_url}/user",
            "revocation_endpoint": f"{base_url}/oauth/revoke",
            "scopes_supported": ["user:email", "read:user"],
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
        }
    )


async def revoke_endpoint(request: Request):
    """Mock token revocation endpoint"""
    form_data = await request.form()
    token = form_data.get("token")

    if token and token in access_tokens:
        del access_tokens[token]

    return JSONResponse({"success": True})


async def health_check(request: Request):
    """Health check endpoint"""
    return JSONResponse(
        {"status": "healthy", "service": "mock-oauth-server", "timestamp": time.time()}
    )


async def debug_tokens(request: Request):
    """Debug endpoint to view active tokens (for testing only)"""
    return JSONResponse(
        {
            "active_auth_codes": len(auth_codes),
            "active_access_tokens": len(access_tokens),
            "auth_codes": {k: {**v, "user_id": v["user_id"]} for k, v in auth_codes.items()},
            "access_tokens": {k: {**v, "user_id": v["user_id"]} for k, v in access_tokens.items()},
        }
    )


# Define routes
routes = [
    Route("/.well-known/openid_configuration", openid_configuration, methods=["GET"]),
    Route("/oauth/authorize", authorize_endpoint, methods=["GET"]),
    Route("/oauth/token", token_endpoint, methods=["POST"]),
    Route("/oauth/revoke", revoke_endpoint, methods=["POST"]),
    Route("/user", user_info_endpoint, methods=["GET"]),  # GitHub uses /user, not /api/user
    Route("/health", health_check, methods=["GET"]),
    Route("/debug/tokens", debug_tokens, methods=["GET"]),
]

# Create Starlette application
app = Starlette(routes=routes)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
