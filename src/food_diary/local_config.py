"""
Local development configuration for LocalStack.
"""

import os
import boto3
from botocore.config import Config


def get_local_boto3_client(service_name):
    """Get a boto3 client configured for LocalStack."""
    endpoint_url = os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
    
    return boto3.client(
        service_name,
        endpoint_url=endpoint_url,
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
        config=Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'}
        )
    )


def get_local_boto3_session():
    """Get a boto3 session configured for LocalStack."""
    endpoint_url = os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
    
    session = boto3.Session(
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )
    
    return session


def is_local_development():
    """Check if we're running in local development mode."""
    return os.getenv('AWS_ENDPOINT_URL') is not None or os.getenv('DEBUG') == 'true'