# Use the official Playwright Python image.
# For available tags, see: https://mcr.microsoft.com/v2/playwright/python/tags/list
# It's good practice to pin to a specific version.
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1

# Set environment for uv/virtualenv
ENV UV_PROJECT_ENVIRONMENT=/venv/
ENV PATH="/venv/bin:$PATH"

# Set the working directory in the container
WORKDIR /app

RUN uv venv

RUN --mount=type=cache,target=/root/.cache/uv uv pip install playwright

# Install Playwright browsers and their OS dependencies
RUN uv run playwright install --with-deps

# Copy files required for dependency installation first to leverage Docker cache
COPY pyproject.toml README.md ./

# Install Python dependencies, including test extras.
# The -e flag installs the project in editable mode.
# Quotes around '.[test]' ensure correct parsing by the shell.
# Using --system to install into the global site-packages, common in Docker.
RUN --mount=type=cache,target=/root/.cache/uv uv sync --no-editable --no-install-project --no-install-workspace --extra test

# Copy the application source code and tests
# This is done after pip install to leverage Docker cache more effectively
COPY src/ ./src/
COPY tests/ ./tests/

# Set the default command to run Playwright E2E tests.
# The application (food_diary.main:app) is expected to be running and accessible
# externally to this container.
#
# When running this Docker container, ensure it can reach the application server.
# For example, if your app is running on http://localhost:8000 on your host machine,
# you can run the Docker container with:
#   docker run --rm --network="host" your-image-name
#
# The BASE_URL in tests/e2e/test_app.py is "http://localhost:8000".
# Using --network="host" makes "localhost" inside the container refer to the host.
CMD ["python", "tests/e2e/test_app.py"]
