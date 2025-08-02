#!/usr/bin/env python3
"""
AWS CDK app for deploying the food diary application.
Optimized for low traffic with serverless architecture.
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
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_lambda as _lambda
from aws_cdk import BundlingOptions
from aws_cdk import aws_rds as rds
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct


class FoodDiaryStack(Stack):
    """Main stack for the food diary application."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create VPC for RDS
        vpc = ec2.Vpc(
            self,
            "FoodDiaryVPC",
            max_azs=2,  # Minimal for RDS
            nat_gateways=0,  # Cost optimization - no NAT gateways needed
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PUBLIC,
                    name="Public",
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    name="Database",
                    cidr_mask=24,
                ),
            ],
        )

        # Security group for RDS
        db_security_group = ec2.SecurityGroup(
            self,
            "DatabaseSecurityGroup",
            vpc=vpc,
            description="Security group for RDS database",
            allow_all_outbound=False,
        )

        # Allow Lambda to access RDS from anywhere (Lambda will be outside VPC)
        db_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(5432),
            description="PostgreSQL access from Lambda",
        )

        # RDS Serverless v2 PostgreSQL database
        db_cluster = rds.DatabaseCluster(
            self,
            "FoodDiaryDB",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_15_4
            ),
            writer=rds.ClusterInstance.serverless_v2("writer", 
                scale_with_writer=False
            ),
            serverless_v2_min_capacity=0.5,  # Minimum for cost optimization
            serverless_v2_max_capacity=1.0,  # Low max for low traffic
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_groups=[db_security_group],
            default_database_name="fooddiary",
            removal_policy=RemovalPolicy.DESTROY,  # Be careful in production
            backup=rds.BackupProps(
                retention=Duration.days(7),  # Minimal backup retention
            ),
        )

        # S3 bucket for static files
        static_bucket = s3.Bucket(
            self,
            "FoodDiaryStatic",
            bucket_name=f"food-diary-static-{self.account}-{self.region}",
            public_read_access=True,
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
                origin=origins.S3Origin(static_bucket),
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
                "DATABASE_URL": f"postgresql://{db_cluster.cluster_endpoint.hostname}:5432/fooddiary",
                "DB_SECRET_NAME": db_cluster.secret.secret_name,
                "STATIC_BUCKET": static_bucket.bucket_name,
                "CLOUDFRONT_DOMAIN": distribution.distribution_domain_name,
                "BASE_URL": "https://api.food-diary.example.com",  # Update this
            },
        )

        # Grant Lambda access to RDS credentials
        db_cluster.secret.grant_read(lambda_function)

        # Grant Lambda access to OAuth secrets
        oauth_secrets.grant_read(lambda_function)

        # Grant Lambda access to S3 bucket
        static_bucket.grant_read_write(lambda_function)

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

        # Lambda integration
        lambda_integration = apigateway.LambdaIntegration(lambda_function)

        # Add proxy resource for all routes
        proxy_resource = api.root.add_resource("{proxy+}")
        proxy_resource.add_method("ANY", lambda_integration)

        # Root route
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
            "DatabaseEndpoint",
            value=db_cluster.cluster_endpoint.hostname,
            description="RDS cluster endpoint",
        )

        CfnOutput(
            self,
            "StaticBucket",
            value=static_bucket.bucket_name,
            description="S3 bucket for static files",
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
    description="Food diary application with Lambda, RDS Serverless, and S3",
)

app.synth()
