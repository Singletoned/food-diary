# Helper function to filter files by extension
_filter_files files ext:
    @echo '{{ files }}' | tr ' ' '\n' | grep '\.{{ ext }}' || true

# Format Python files (specific files or all *.py)
format-python files="**/*.py":
    uvx ruff format {{ files }}
    uvx ruff check {{ files }}
    uvx ruff format {{ files }}

# Format Pug files (specific files or all *.pug)
format-pug files="**/*.pug":
    npx prettier --plugin=@prettier/plugin-pug --write {{ files }}

# Format JS files (specific files or all *.js)
format-js files="**/*.js":
    npx prettier --write {{ files }}

# Format all files (calls individual formatters)
format-all: format-python format-pug format-js

# Format specific files or all files of each type
format *files:
    @[ -n "$(just _filter_files '{{ files }}' py)" ] && just format-python "$(just _filter_files '{{ files }}' py)" || true
    @[ -n "$(just _filter_files '{{ files }}' pug)" ] && just format-pug "$(just _filter_files '{{ files }}' pug)" || true
    @[ -n "$(just _filter_files '{{ files }}' js)" ] && just format-js "$(just _filter_files '{{ files }}' js)" || true

serve:
    uvicorn src.food_diary.main:app --reload

test:
    pytest tests/test_main.py

test-e2e-compose:
    @echo "Running E2E tests with Docker Compose..."
    @docker compose -f ./tests/compose.yaml build
    docker compose -f ./tests/compose.yaml up \
        --abort-on-container-exit \
        --exit-code-from playwright-tests; \
    EXIT_CODE=$$?; \
    echo "Cleaning up Docker Compose services (exit code: $$EXIT_CODE)..."; \
    docker compose -f ./tests/compose.yaml down -v --remove-orphans; \
    exit $$EXIT_CODE
