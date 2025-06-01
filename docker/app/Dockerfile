FROM ubuntu:24.04
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1

# Install curl for healthchecks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Set environment for uv/virtualenv
ENV UV_PROJECT_ENVIRONMENT=/venv/
ENV PATH="/venv/bin:$PATH"

# Install python
RUN uv python install 3.12

# Set up a virtual environment
RUN uv venv /venv/

# Set the working directory
WORKDIR /app

# Copy only the files needed to install dependencies
COPY pyproject.toml /app/

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv uv sync --no-editable --no-install-project --no-install-workspace --no-dev

# Copy the rest of the application code
COPY ./ /app/

# Install project properly
RUN --mount=type=cache,target=/root/.cache/uv uv sync --no-dev
