"""
AWS Lambda handler for the food diary application.
Uses Mangum to adapt the Starlette ASGI app for Lambda.
"""

import logging
import os

from mangum import Mangum

# Configure logging for Lambda
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

# Configure for Lambda environment
os.environ.setdefault("AWS_LAMBDA_RUNTIME", "1")

# Log environment variables for debugging
logger.info(f"DATA_BUCKET exists: {'DATA_BUCKET' in os.environ}")
logger.info(f"DATA_BUCKET value: {os.environ.get('DATA_BUCKET', 'NOT_SET')}")
logger.info(f"AWS_LAMBDA_RUNTIME: {os.environ.get('AWS_LAMBDA_RUNTIME')}")

try:
    from src.food_diary.main import app

    logger.info("Successfully imported main app")

    # Create the Lambda handler
    handler = Mangum(app, lifespan="off")
    logger.info("Successfully created Mangum handler")

except Exception as e:
    logger.error(f"Error during initialization: {e}")
    import traceback

    logger.error(traceback.format_exc())
    raise
