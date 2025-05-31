format *files:
    #!/usr/bin/env bash
    python_files=$(echo {{files}} \
        | tr ' ' '\n' \
        | grep '\.py$' \
        | tr '\n' ' ')
    uvx ruff format $python_files
    uvx ruff check $python_files
    uvx ruff format $python_files
    pug_files=$(echo {{files}} \
        | tr ' ' '\n' \
        | grep '\.pug$' \
        | tr '\n' ' ')
    if [ -n "$pug_files" ]; then \
        npx prettier --plugin=@prettier/plugin-pug --write $pug_files; \
    fi

test:
    pytest
