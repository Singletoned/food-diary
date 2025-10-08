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
    cd infrastructure && cdk bootstrap --quiet --output /tmp/cdk-out

deploy-aws: bootstrap-aws
    #!/usr/bin/env bash
    set -e
    echo "🏗️ Deploying to AWS..."

    cd infrastructure && cdk deploy --require-approval never --outputs-file ../build/cdk-outputs.json --output /tmp/cdk-out

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
    cd infrastructure && cdk destroy --output /tmp/cdk-out

setup-aws-secrets:
    #!/usr/bin/env bash
    set -e

    echo "🔐 AWS Secrets Setup"
    echo "===================="
    echo ""
    echo "This will create/update the 'chompix/oauth' secret in AWS Secrets Manager."
    echo ""
    echo "⚠️  IMPORTANT: Run this BEFORE 'just deploy-aws' on first deployment"
    echo "    The CDK stack requires this secret to exist."
    echo ""
    echo "You'll need:"
    echo "  1. GitHub OAuth Client ID"
    echo "  2. GitHub OAuth Client Secret"
    echo "  3. A SECRET_KEY will be generated automatically"
    echo ""

    # Prompt for GitHub OAuth credentials
    read -p "Enter GitHub Client ID: " GITHUB_CLIENT_ID
    read -p "Enter GitHub Client Secret: " GITHUB_CLIENT_SECRET

    # Generate a secure random SECRET_KEY
    echo ""
    echo "🔑 Generating secure SECRET_KEY..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")

    # Create JSON payload
    SECRET_JSON=$(python3 -c "import json; print(json.dumps({
        'GITHUB_CLIENT_ID': '$GITHUB_CLIENT_ID',
        'GITHUB_CLIENT_SECRET': '$GITHUB_CLIENT_SECRET',
        'SECRET_KEY': '$SECRET_KEY'
    }))")

    echo ""
    echo "📤 Pushing secrets to AWS Secrets Manager..."

    # Check if secret exists
    if aws secretsmanager describe-secret --secret-id chompix/oauth &>/dev/null; then
        echo "   Updating existing secret..."
        aws secretsmanager update-secret \
            --secret-id chompix/oauth \
            --secret-string "$SECRET_JSON"
    else
        echo "   Creating new secret..."
        aws secretsmanager create-secret \
            --name chompix/oauth \
            --description "Chompix GitHub OAuth credentials and session secret" \
            --secret-string "$SECRET_JSON"
    fi

    echo ""
    echo "✅ Secrets successfully stored in AWS Secrets Manager!"
    echo ""
    echo "📝 Summary:"
    echo "   Secret name: chompix/oauth"
    echo "   GitHub Client ID: $GITHUB_CLIENT_ID"
    echo "   GitHub Client Secret: ********"
    echo "   SECRET_KEY: ********"
    echo ""
    echo "💡 Next step: Run 'just deploy-aws' to deploy the application"

clean:
    rm -rf build/ food_diary.db
