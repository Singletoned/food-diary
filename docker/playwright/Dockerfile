# Use the official Playwright Python image.
# For available tags, see: https://mcr.microsoft.com/v2/playwright/python/tags/list
# It's good practice to pin to a specific version.
FROM mcr.microsoft.com/playwright/python:v1.53.0-jammy

RUN pip install pytest playwright pytest-playwright

CMD ["pytest"]
