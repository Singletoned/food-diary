# Format specific files or all files of each type
format *files:
    taidy .

serve:
    uvicorn src.food_diary.main:app --reload --host 0.0.0.0 --port 9000

test:
    pytest tests/test_main.py

test-e2e-compose:
    @docker compose -f ./tests/compose.yaml build --quiet
    @docker compose -f ./tests/compose.yaml up \
        --abort-on-container-exit \
        --exit-code-from tests \
        --quiet-pull \
        --remove-orphans \
        tests
