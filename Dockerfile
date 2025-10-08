FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy application code first 
COPY . .

# Install dependencies
RUN pip install -e .

# Create data directory for SQLite
RUN mkdir -p /data

# Set environment variables
ENV DB_PATH=/data/food_diary.db
ENV PORT=9000

EXPOSE 9000

CMD ["uvicorn", "src.food_diary.main:app", "--host", "0.0.0.0", "--port", "9000"]