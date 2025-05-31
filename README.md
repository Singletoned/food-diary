# Food Diary

A minimal Python web app using Starlette and Pug templates.

## Development

To set up the development environment:

```bash
# Install project dependencies (including dev dependencies)
uv pip install -e .[test]
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
    uv pip install -e .[test]
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
