format *files:
    #!/usr/bin/env bash
    python_files=$(echo {{files}} \
        | tr ' ' '\n' \
        | grep '\.py$' \
        | tr '\n' ' ')
    uvx ruff format $python_files
    uvx ruff check $python_files
    uvx ruff format $python_files
    # AI! Add something to this recipe that filters files for pug files, then if there are any, passes them to `prettier --plugin=@prettier/plugin-pug --write`

test:
    pytest
