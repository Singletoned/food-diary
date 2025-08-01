# AWS Deployment Guide

This guide covers deploying your food diary application to AWS using CDK (Cloud Development Kit) with a serverless, low-traffic optimized architecture.

## Architecture Overview

- **AWS Lambda** + **API Gateway**: Serverless compute (pay per request)
- **RDS Serverless v2**: Auto-scaling PostgreSQL database (pauses when idle)
- **S3** + **CloudFront**: Static file hosting with global CDN
- **Secrets Manager**: Secure storage for OAuth credentials

## Prerequisites

1. **AWS CLI** configured with appropriate permissions
2. **Node.js** (for CDK CLI)
3. **Python dependencies**: `uv pip install -e '.[cdk]'`

## Quick Deploy

```bash
# Make sure AWS CLI is configured
aws configure

# Run the deployment script
./deploy.sh
```

## Manual Deployment Steps

### 1. Install CDK CLI

```bash
npm install -g aws-cdk
```

### 2. Bootstrap CDK (first time only)

```bash
cdk bootstrap
```

### 3. Deploy Infrastructure

```bash
# Install Python dependencies
uv pip install -e '.[cdk]'

# Deploy the stack
cdk deploy --outputs-file cdk-outputs.json
```

### 4. Upload Static Files

```bash
# Get bucket name from outputs
BUCKET_NAME=$(jq -r '.FoodDiaryStack.StaticBucket' cdk-outputs.json)

# Upload static files
aws s3 sync static/ s3://$BUCKET_NAME/
```

### 5. Configure OAuth

1. Get API URL from deployment outputs
2. Update GitHub OAuth app callback URL to: `https://your-api-url/auth/callback`
3. Set OAuth secrets in AWS Secrets Manager:

```bash
# Get secret ARN from AWS console, then update:
aws secretsmanager update-secret \
  --secret-id "your-secret-arn" \
  --secret-string '{
    "SECRET_KEY": "your-generated-secret-key",
    "GITHUB_CLIENT_ID": "your-github-client-id",
    "GITHUB_CLIENT_SECRET": "your-github-client-secret"
  }'
```

## Cost Optimization Features

- **RDS Serverless v2**: Auto-pauses after 5 minutes of inactivity
- **Lambda**: Pay only for requests (generous free tier)
- **API Gateway HTTP API**: Cheaper than REST API
- **CloudFront**: Free tier includes 1TB transfer
- **S3**: Pay only for storage used

## Expected Monthly Costs (Very Low Traffic)

- Lambda: ~$0-1 (free tier covers 1M requests)
- RDS Serverless: ~$7-15 (0.5 ACU minimum when active)
- API Gateway: ~$0-1 (free tier covers 1M requests)
- S3 + CloudFront: ~$1-3
- **Total: ~$8-20/month**

## Database Management

### Connect to RDS

```bash
# Get DB endpoint from outputs
DB_ENDPOINT=$(jq -r '.FoodDiaryStack.DatabaseEndpoint' cdk-outputs.json)

# Connect using psql (get password from Secrets Manager)
psql -h $DB_ENDPOINT -U postgres -d fooddiary
```

### Initialize Database

The database tables are created automatically when the Lambda function first runs.

## Monitoring

- **CloudWatch**: Automatic logging for Lambda and API Gateway
- **RDS Performance Insights**: Database performance monitoring
- **X-Ray**: Distributed tracing (optional)

## Local Development

The app still works locally with SQLite:

```bash
# Run locally (uses SQLite)
just serve

# Test locally (uses SQLite)
just test
```

## Cleanup

To avoid ongoing charges:

```bash
# Delete all AWS resources
cdk destroy
```

## Troubleshooting

### Lambda Cold Starts

- First request after idle period may be slower (~2-3 seconds)
- Subsequent requests are fast (~100-200ms)

### Database Connection Issues

- Lambda needs VPC access to reach RDS
- Security groups must allow PostgreSQL traffic (port 5432)

### Static Files Not Loading

- Check S3 bucket permissions are public
- Verify CloudFront distribution is deployed
- Static file URLs should redirect to CloudFront

## Environment Variables

The Lambda function uses these environment variables (set automatically by CDK):

- `DATABASE_URL`: PostgreSQL connection string
- `STATIC_BUCKET`: S3 bucket name for static files
- `CLOUDFRONT_DOMAIN`: CloudFront distribution domain
- `BASE_URL`: API Gateway URL for OAuth redirects
- `AWS_REGION`: AWS region

OAuth credentials are loaded from Secrets Manager automatically.
