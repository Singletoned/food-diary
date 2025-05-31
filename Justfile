format *files:
    #!/usr/bin/env bash
    filtered_files=$(echo {{files}} \
        | tr ' ' '\n' \
        | grep '\.py$' \
        | tr '\n' ' ')
    uvx ruff format $filtered_files
    uvx ruff check $filtered_files
    uvx ruff format $filtered_files

test:
    pytest
