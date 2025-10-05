# Format specific files or all files of each type
format *files:
    taidy .

serve:
    docker compose build
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
    cd infrastructure && cdk bootstrap --quiet

deploy-aws: bootstrap-aws
    #!/usr/bin/env bash
    set -e
    echo "🏗️ Deploying to AWS..."

    cd infrastructure && cdk deploy --require-approval never --outputs-file ../build/cdk-outputs.json

    # Upload static files if deployment succeeded
    if [ -f build/cdk-outputs.json ]; then
        BUCKET=$(jq -r '.FoodDiaryStack.DataBucket' build/cdk-outputs.json)
        API_URL=$(jq -r '.FoodDiaryStack.ApiUrl' build/cdk-outputs.json)
        echo "📁 Uploading static files..."
        aws s3 sync static/ s3://$BUCKET/static/ --delete
        echo "🎉 Deployment complete!"
        echo "🌐 API URL: $API_URL"
        echo "⚙️ Update GitHub OAuth callback to: ${API_URL}/auth/callback"
    fi

destroy-aws:
    cd infrastructure && cdk destroy

clean:
    rm -rf build/ food_diary.db
