# Food Diary

A minimal Python web app using Starlette and Pug templates.

## Development

To set up the development environment:

```bash
# Install project dependencies (including dev dependencies)
uv pip install -e '.[test]'
```

To run the application:

```bash
uvicorn src.food_diary.main:app --reload
```

To run tests:

```bash
just test
```

To format code:

```bash
just format
```

## End-to-End (E2E) Testing with Playwright

This project uses Playwright for end-to-end testing.

### Setup

1.  Install project test dependencies (which now include Playwright):
    ```bash
    uv pip install -e '.[test]'
    ```
2.  Install Playwright browsers:
    ```bash
    playwright install
    ```

### Running E2E Tests

1.  Ensure the application server is running:
    ```bash
    just serve
    ```
2.  In a separate terminal, run the E2E tests:
    ```bash
    just test-e2e
    ```
    (This now uses `nose2` to run tests from `tests/e2e/`)

### Running E2E Tests with Docker Compose

Alternatively, you can run the application and the E2E tests together in a controlled environment using Docker Compose. This is often preferred for CI or for ensuring a consistent test environment.

1.  Ensure Docker and Docker Compose are installed.
2.  Run the tests using the provided Justfile recipe:
    ```bash
    just test-e2e-compose
    ```
    This command will:
    - Build the Docker images for the app and the Playwright tests if they don't exist or if their Dockerfiles have changed.
    - Start the application service.
    - Run the Playwright tests (using `nose2`) against the application service.
    - Show test output in your terminal.
    - Stop and remove the containers after tests complete.
      The exit code will reflect the test suite's success or failure.
