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

        # CloudFront distribution for static files
        distribution = cloudfront.Distribution(
            self,
            "FoodDiaryDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(data_bucket),
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
        )

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

        # Lambda function using container image deployment
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
                "CLOUDFRONT_DOMAIN": distribution.distribution_domain_name,
                "BASE_URL": "https://api.food-diary.example.com",  # Update this
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
