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

setup-github-oidc:
    #!/usr/bin/env bash
    set -e

    echo "🔐 GitHub Actions OIDC Setup"
    echo "============================"
    echo ""
    echo "This will set up AWS OIDC authentication for GitHub Actions deployments."
    echo ""

    # Get AWS account ID
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    echo "📋 AWS Account ID: $ACCOUNT_ID"
    echo ""

    # Prompt for GitHub repository details
    read -p "Enter GitHub username/org (e.g., 'singletoned'): " GITHUB_USER
    read -p "Enter repository name (e.g., 'food-diary'): " REPO_NAME

    REPO_FULL="${GITHUB_USER}/${REPO_NAME}"
    echo ""
    echo "🔧 Setting up OIDC for repository: $REPO_FULL"
    echo ""

    # Check if OIDC provider already exists
    echo "1️⃣  Checking OIDC provider..."
    PROVIDER_ARN="arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"

    if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$PROVIDER_ARN" &>/dev/null; then
        echo "   ✅ OIDC provider already exists"
    else
        echo "   Creating OIDC provider..."
        aws iam create-open-id-connect-provider \
            --url https://token.actions.githubusercontent.com \
            --client-id-list sts.amazonaws.com \
            --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
        echo "   ✅ OIDC provider created"
    fi

    # Create trust policy
    echo ""
    echo "2️⃣  Creating IAM role trust policy..."
    TRUST_POLICY=$(cat <<EOF
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Federated": "${PROVIDER_ARN}"
          },
          "Action": "sts:AssumeRoleWithWebIdentity",
          "Condition": {
            "StringEquals": {
              "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
            },
            "StringLike": {
              "token.actions.githubusercontent.com:sub": "repo:${REPO_FULL}:ref:refs/heads/main"
            }
          }
        }
      ]
    }
    EOF
    )

    # Create IAM role
    echo "3️⃣  Creating IAM role..."
    ROLE_NAME="GitHubActionsDeployRole"

    if aws iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
        echo "   Role already exists, updating trust policy..."
        aws iam update-assume-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-document "$TRUST_POLICY"
    else
        echo "   Creating new role..."
        aws iam create-role \
            --role-name "$ROLE_NAME" \
            --assume-role-policy-document "$TRUST_POLICY"

        echo "   Attaching AdministratorAccess policy..."
        aws iam attach-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
    fi

    ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
    echo "   ✅ Role created: $ROLE_ARN"

    echo ""
    echo "🎉 Setup complete!"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Go to GitHub repository settings:"
    echo "      https://github.com/${REPO_FULL}/settings/secrets/actions"
    echo ""
    echo "   2. Add this secret:"
    echo "      Name:  AWS_ROLE_ARN"
    echo "      Value: $ROLE_ARN"
    echo ""
    echo "   3. (Optional) Add this variable:"
    echo "      Name:  AWS_REGION"
    echo "      Value: us-east-1"
    echo ""
    echo "   4. Run 'just setup-aws-secrets' to create OAuth secrets"
    echo ""
    echo "   5. Push to main branch to trigger deployment!"

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
