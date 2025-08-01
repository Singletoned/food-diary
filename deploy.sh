#!/bin/bash

# Deployment script for Food Diary app to AWS using CDK

set -e # Exit on any error

echo "🚀 Deploying Food Diary to AWS with CDK..."

# Check if CDK is installed
if ! command -v cdk &>/dev/null; then
	echo "❌ AWS CDK not found. Installing..."
	npm install -g aws-cdk
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &>/dev/null; then
	echo "❌ AWS CLI not configured. Please run 'aws configure' first."
	exit 1
fi

# Install Python dependencies including CDK
echo "📦 Installing dependencies..."
uv pip install -e '.[cdk]'

# Upload static files to S3 (after stack is deployed)
upload_static_files() {
	local bucket_name=$1
	echo "📁 Uploading static files to S3..."
	aws s3 sync static/ s3://$bucket_name/ --delete
	echo "✅ Static files uploaded to S3"
}

# Bootstrap CDK (if not already done)
echo "🔧 Bootstrapping CDK (if needed)..."
cdk bootstrap --quiet

# Deploy the stack
echo "🏗️ Deploying CDK stack..."
cdk deploy --require-approval never --outputs-file cdk-outputs.json

# Extract outputs
if [ -f cdk-outputs.json ]; then
	API_URL=$(jq -r '.FoodDiaryStack.ApiUrl' cdk-outputs.json)
	STATIC_BUCKET=$(jq -r '.FoodDiaryStack.StaticBucket' cdk-outputs.json)
	CLOUDFRONT_DOMAIN=$(jq -r '.FoodDiaryStack.CloudFrontDomain' cdk-outputs.json)
	DB_ENDPOINT=$(jq -r '.FoodDiaryStack.DatabaseEndpoint' cdk-outputs.json)

	echo ""
	echo "🎉 Deployment successful!"
	echo "📡 API URL: $API_URL"
	echo "🪣 S3 Bucket: $STATIC_BUCKET"
	echo "🌐 CloudFront: https://$CLOUDFRONT_DOMAIN"
	echo "🗄️ Database: $DB_ENDPOINT"
	echo ""

	# Upload static files
	upload_static_files "$STATIC_BUCKET"

	echo "⚙️ Next steps:"
	echo "1. Update GitHub OAuth app callback URL to: ${API_URL}/auth/callback"
	echo "2. Set OAuth secrets in AWS Secrets Manager"
	echo "3. Test your application at: $API_URL"

else
	echo "❌ Could not find deployment outputs"
	exit 1
fi
