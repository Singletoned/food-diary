format *files:
    #!/usr/bin/env bash
    python_files=$(echo {{files}} \
        | tr ' ' '\n' \
        | grep '\.py$' \
        | tr '\n' ' ')
    if [ -n "$python_files" ]; then \
        uvx ruff format $python_files; \
        uvx ruff check $python_files; \
        uvx ruff format $python_files; \
    fi
    pug_files=$(echo {{files}} \
        | tr ' ' '\n' \
        | grep '\.pug$' \
        | tr '\n' ' ')
    if [ -n "$pug_files" ]; then \
        npx prettier --plugin=@prettier/plugin-pug --write $pug_files; \
    fi
    js_files=$(echo {{files}} \
        | tr ' ' '\n' \
        | grep '\.js$' \
        | tr '\n' ' ')
    if [ -n "$js_files" ]; then \
        npx prettier --write $js_files; \
    fi

serve:
    uvicorn src.food_diary.main:app --reload

test:
    pytest
