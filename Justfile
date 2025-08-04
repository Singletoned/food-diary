# Format specific files or all files of each type
format *files:
    taidy .

serve:
    docker compose up

test:
    pytest tests/test_main.py

test-e2e-compose:
    @docker compose -f ./tests/compose.yaml build --quiet
    @docker compose -f ./tests/compose.yaml up \
        --abort-on-container-exit \
        --exit-code-from food-diary-tests \
        --quiet-pull \
        --remove-orphans \
        food-diary-tests

bootstrap-aws:
    cdk bootstrap --quiet

deploy-aws: bootstrap-aws
    #!/usr/bin/env bash
    set -e
    echo "🏗️ Deploying to AWS..."

    cdk deploy --require-approval never --outputs-file cdk-outputs.json

    # Upload static files if deployment succeeded
    if [ -f cdk-outputs.json ]; then
        BUCKET=$(jq -r '.FoodDiaryStack.DataBucket' cdk-outputs.json)
        API_URL=$(jq -r '.FoodDiaryStack.ApiUrl' cdk-outputs.json)
        echo "📁 Uploading static files..."
        aws s3 sync static/ s3://$BUCKET/ --delete
        echo "🎉 Deployment complete!"
        echo "🌐 API URL: $API_URL"
        echo "⚙️ Update GitHub OAuth callback to: ${API_URL}/auth/callback"
    fi

destroy-aws:
    cdk destroy
