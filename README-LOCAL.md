# Local Development Setup

This document describes how to run the Food Diary application locally using Docker and LocalStack.

## Architecture

The local setup includes:

- **LocalStack**: Emulates AWS services (S3, Secrets Manager, API Gateway)
- **Food Diary App**: The main application running in development mode
- **Mock OAuth Server**: Simulates GitHub OAuth for testing

## Prerequisites

- Docker and Docker Compose
- At least 4GB of available RAM

## Quick Start

1. **Start all services:**
   ```bash
   docker compose up --build
   ```

2. **Wait for services to be ready** (check the logs):
   - LocalStack: `LocalStack initialization complete!`
   - Food Diary: Application starts on port 8000
   - Mock OAuth: Available on port 8080

3. **Access the application:**
   - Food Diary: http://localhost:8000
   - Mock OAuth: http://localhost:8080/health
   - LocalStack Dashboard: http://localhost:4566/_localstack/health

## Services Overview

### LocalStack (Port 4566)
- **S3 Bucket**: `food-diary-local-bucket`
- **Secrets Manager**: OAuth credentials
- **API Gateway**: Mock REST API (for testing)

Useful commands:
```bash
# List S3 buckets
awslocal s3 ls

# Check bucket contents
awslocal s3 ls s3://food-diary-local-bucket --recursive

# Get secrets
awslocal secretsmanager get-secret-value --secret-id food-diary-oauth-secrets
```

### Food Diary App (Port 8000)
- Connects to LocalStack for S3 storage
- Uses mock OAuth for authentication
- Hot-reload enabled for development

Environment variables (see `envs/food-diary/.env`):
- `AWS_ENDPOINT_URL=http://localstack:4566`
- `DATA_BUCKET=food-diary-local-bucket`
- `OAUTH_PROVIDER=mock`

### Mock OAuth Server (Port 8080)
Simulates GitHub OAuth flow with test users:

**Test Users:**
- `testuser` (ID: 123): test@example.com
- `adminuser` (ID: 456): admin@example.com

**Endpoints:**
- Authorization: http://localhost:8080/oauth/authorize
- Token: http://localhost:8080/oauth/token  
- User Info: http://localhost:8080/user
- Health: http://localhost:8080/health
- Debug: http://localhost:8080/debug/tokens

## Development Workflow

### Making Code Changes
1. Edit files in `src/`, `templates/`, or `static/`
2. Changes are automatically reloaded (uvicorn --reload)
3. No need to restart containers

### Testing OAuth Flow
1. Go to http://localhost:8000
2. Click "Sign in with GitHub"
3. You'll be automatically logged in as the test user
4. The app will create user data in LocalStack S3

### Debugging

**View LocalStack logs:**
```bash
docker compose logs localstack
```

**View Food Diary logs:**
```bash
docker compose logs food-diary
```

**Check S3 data:**
```bash
# Install awscli-local if not already installed
pip install awscli-local

# List bucket contents
awslocal s3 ls s3://food-diary-local-bucket --recursive

# Download a file
awslocal s3 cp s3://food-diary-local-bucket/users/123/profile.json ./profile.json
```

**Mock OAuth debug:**
```bash
curl http://localhost:8080/debug/tokens
```

## Troubleshooting

### "Connection refused" errors
- Ensure all services are up: `docker compose ps`
- Check if ports are available: `lsof -i :4566,8000,8080`

### S3 bucket not found
- Wait for LocalStack initialization to complete
- Check logs: `docker compose logs localstack`
- Manually create bucket: `awslocal s3 mb s3://food-diary-local-bucket`

### OAuth login fails
- Verify mock-oauth is running: `curl http://localhost:8080/health`
- Check Food Diary environment variables

### Data persistence
- LocalStack data persists in the `localstack-data` Docker volume
- To reset: `docker compose down -v`

## File Structure

```
docker/
├── localstack/          # LocalStack configuration
│   ├── Dockerfile       # Custom LocalStack image
│   └── init/           # Initialization scripts
│       └── 01-setup-resources.sh
├── food-diary/         # Food Diary application
│   └── Dockerfile      # Development Dockerfile
└── mock-oauth/         # Mock OAuth server
    ├── Dockerfile
    ├── app.py          # OAuth simulation
    └── requirements.txt

envs/
├── localstack/.env     # LocalStack environment
└── food-diary/.env     # Food Diary environment
```

## Deployment vs Local Development

| Feature | Local (Docker) | AWS Production |
|---------|----------------|----------------|
| Storage | LocalStack S3 | AWS S3 |
| OAuth | Mock server | GitHub OAuth |
| URL | localhost:8000 | CloudFront |
| Database | S3 JSON files | S3 JSON files |
| Cost | Free | ~$0.02/month |