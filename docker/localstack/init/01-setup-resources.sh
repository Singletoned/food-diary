#!/bin/bash

# LocalStack initialization script for Food Diary resources
set -e

echo "Setting up LocalStack resources for Food Diary..."

# Wait for LocalStack to be ready
awslocal s3 ls || echo "Waiting for LocalStack..."

# Create S3 bucket for data and static files
echo "Creating S3 bucket..."
awslocal s3 mb s3://food-diary-local-bucket

# Enable versioning on the bucket
awslocal s3api put-bucket-versioning \
	--bucket food-diary-local-bucket \
	--versioning-configuration Status=Enabled

# Set bucket policy for public read access to static files
awslocal s3api put-bucket-policy \
	--bucket food-diary-local-bucket \
	--policy '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::food-diary-local-bucket/static/*"
            }
        ]
    }'

# Create Secrets Manager secret for OAuth
echo "Creating OAuth secrets..."
awslocal secretsmanager create-secret \
	--name "food-diary-oauth-secrets" \
	--description "OAuth credentials for Food Diary local development" \
	--secret-string '{
        "SECRET_KEY": "local-dev-secret-key-change-in-production",
        "GITHUB_CLIENT_ID": "mock-client-id",
        "GITHUB_CLIENT_SECRET": "mock-client-secret"
    }'

# Create API Gateway (basic setup)
echo "Creating API Gateway..."
REST_API_ID=$(awslocal apigateway create-rest-api \
	--name "food-diary-local-api" \
	--description "Food Diary Local API" \
	--query 'id' \
	--output text)

echo "Created REST API with ID: $REST_API_ID"

# Get root resource ID
ROOT_RESOURCE_ID=$(awslocal apigateway get-resources \
	--rest-api-id $REST_API_ID \
	--query 'items[0].id' \
	--output text)

# Create proxy resource {proxy+}
PROXY_RESOURCE_ID=$(awslocal apigateway create-resource \
	--rest-api-id $REST_API_ID \
	--parent-id $ROOT_RESOURCE_ID \
	--path-part '{proxy+}' \
	--query 'id' \
	--output text)

echo "Created proxy resource with ID: $PROXY_RESOURCE_ID"

echo "LocalStack initialization complete!"
echo "S3 bucket: food-diary-local-bucket"
echo "API Gateway ID: $REST_API_ID"
echo "Secrets Manager: food-diary-oauth-secrets"
