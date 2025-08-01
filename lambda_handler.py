"""
AWS Lambda handler for the food diary application.
Uses Mangum to adapt the Starlette ASGI app for Lambda.
"""

import os

from mangum import Mangum

from src.food_diary.main import app

# Configure for Lambda environment
os.environ.setdefault("AWS_LAMBDA_RUNTIME", "1")

# Create the Lambda handler
handler = Mangum(app, lifespan="off")
