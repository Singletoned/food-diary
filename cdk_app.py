#!/usr/bin/env python3
"""
AWS CDK app for deploying the food diary application.
Optimized for low traffic with S3-based storage.
"""

import os

from aws_cdk import (
    App,
    Duration,
    Environment,
    RemovalPolicy,
    Stack,
)
from aws_cdk import aws_apigateway as apigateway
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class FoodDiaryStack(Stack):
    """Main stack for the food diary application using S3 for storage."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket for both static files and data storage
        data_bucket = s3.Bucket(
            self,
            "FoodDiaryBucket",
            bucket_name=f"food-diary-{self.account}-{self.region}",
            versioned=True,  # Enable versioning for data backup
            public_read_access=True,  # For static files only
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                ignore_public_acls=False,
                block_public_policy=False,
                restrict_public_buckets=False,
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Note: CloudFront distribution will be configured after API Gateway is created

        # Secrets for OAuth credentials
        oauth_secrets = secretsmanager.Secret(
            self,
            "OAuthSecrets",
            description="GitHub OAuth credentials",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"SECRET_KEY": "change-me"}',
                generate_string_key="SECRET_KEY",
                exclude_characters='"/\\@',
            ),
        )

        # Lambda function using container image deployment (CloudFront domain will be added later)
        lambda_function = _lambda.Function(
            self,
            "FoodDiaryFunction",
            runtime=_lambda.Runtime.FROM_IMAGE,
            handler=_lambda.Handler.FROM_IMAGE,
            architecture=_lambda.Architecture.X86_64,  # Specify x86_64 architecture
            code=_lambda.Code.from_asset_image(".", file="Dockerfile.lambda"),
            timeout=Duration.seconds(30),
            memory_size=512,  # Moderate memory for cost optimization
            environment={
                "DATA_BUCKET": data_bucket.bucket_name,
                "STATIC_BUCKET": data_bucket.bucket_name,  # Same bucket for both
                # BASE_URL will be set to API Gateway URL after creation
            },
        )

        # Grant Lambda access to OAuth secrets
        oauth_secrets.grant_read(lambda_function)

        # Grant Lambda full access to S3 bucket (for both data and static files)
        data_bucket.grant_read_write(lambda_function)

        # API Gateway REST API
        api = apigateway.RestApi(
            self,
            "FoodDiaryApi",
            description="Food Diary API",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["*"],
            ),
        )

        # Lambda proxy integration (ensures proper event format for Mangum)
        lambda_integration = apigateway.LambdaIntegration(lambda_function, proxy=True)

        # Add proxy resource for all routes (this handles ALL paths)
        proxy_resource = api.root.add_resource("{proxy+}")
        proxy_resource.add_method("ANY", lambda_integration)

        # Root route (handles requests to the root path "/")
        api.root.add_method("ANY", lambda_integration)

        # CloudFront distribution for both static files and API
        distribution = cloudfront.Distribution(
            self,
            "FoodDiaryDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.HttpOrigin(
                    domain_name=api.rest_api_id + ".execute-api." + self.region + ".amazonaws.com",
                    origin_path="/prod",
                ),
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,  # Disable caching for API
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
            ),
            additional_behaviors={
                "/static/*": cloudfront.BehaviorOptions(
                    origin=origins.S3Origin(data_bucket),
                    cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                ),
            },
        )

        # Get GitHub OAuth credentials from .env file (already loaded)
        github_client_id = os.environ.get("GITHUB_CLIENT_ID", "your-github-client-id")
        github_client_secret = os.environ.get("GITHUB_CLIENT_SECRET", "your-github-client-secret")
        secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

        # Update Lambda environment with URLs and OAuth config
        lambda_function.add_environment("CLOUDFRONT_DOMAIN", distribution.distribution_domain_name)
        # Construct BASE_URL manually to avoid circular dependency
        base_url = f"https://{api.rest_api_id}.execute-api.{self.region}.amazonaws.com/prod"
        lambda_function.add_environment("BASE_URL", base_url)
        lambda_function.add_environment("API_STAGE_PATH", "/prod")
        lambda_function.add_environment("SECRET_KEY", secret_key)
        lambda_function.add_environment("OAUTH_PROVIDER", "github")  # Explicitly set for production
        lambda_function.add_environment("GITHUB_CLIENT_ID", github_client_id)
        lambda_function.add_environment("GITHUB_CLIENT_SECRET", github_client_secret)

        # Output important values
        from aws_cdk import CfnOutput

        CfnOutput(
            self,
            "ApiUrl",
            value=api.url,
            description="API Gateway URL",
        )

        CfnOutput(
            self,
            "DataBucket",
            value=data_bucket.bucket_name,
            description="S3 bucket for data and static files",
        )

        CfnOutput(
            self,
            "CloudFrontDomain",
            value=distribution.distribution_domain_name,
            description="CloudFront distribution domain",
        )

        CfnOutput(
            self,
            "GitHubOAuthSetup",
            value=f"Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET environment variables, then redeploy. Callback URL: {base_url}/auth/callback",
            description="GitHub OAuth setup instructions",
        )


app = App()

# Get AWS account and region from environment or CDK context
account = os.environ.get("CDK_DEFAULT_ACCOUNT")
region = os.environ.get("CDK_DEFAULT_REGION", "us-east-1")

FoodDiaryStack(
    app,
    "FoodDiaryStack",
    env=Environment(account=account, region=region),
    description="Food diary application with Lambda and S3 storage",
)

app.synth()
