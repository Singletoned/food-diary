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
