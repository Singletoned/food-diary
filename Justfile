format *files:
    #!/usr/bin/env bash
    
    # Function to filter files by extension
    # $1: space-separated list of all files (passed as a single string)
    # $2: extension (e.g., "py", "pug", "js")
    _get_files_with_ext() {
        echo "$1" | tr ' ' '\n' | grep --color=never "\.$2$" | tr '\n' ' ' | sed 's/ $//'
    }

    # Python files
    python_files=$(_get_files_with_ext "{{files}}" "py")
    if [ -n "$python_files" ]; then
        uvx ruff format $python_files
        uvx ruff check $python_files
        uvx ruff format $python_files
    fi

    # Pug files
    pug_files=$(_get_files_with_ext "{{files}}" "pug")
    if [ -n "$pug_files" ]; then
        npx prettier --plugin=@prettier/plugin-pug --write $pug_files
    fi

    # JS files
    js_files=$(_get_files_with_ext "{{files}}" "js")
    if [ -n "$js_files" ]; then
        npx prettier --write $js_files
    fi

serve:
    uvicorn src.food_diary.main:app --reload

test:
    pytest
