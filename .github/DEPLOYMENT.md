# GitHub Actions Deployment Setup

This document explains how to set up automated deployments to AWS using GitHub Actions.

## Prerequisites

- AWS Account with appropriate permissions
- GitHub repository with Actions enabled
- OAuth secrets already created in AWS Secrets Manager (run `just setup-aws-secrets`)

## Setup Steps

### 1. Create AWS OIDC Provider for GitHub

This allows GitHub Actions to authenticate to AWS without storing long-lived credentials.

```bash
# Get your AWS account ID
aws sts get-caller-identity --query Account --output text

# Create the OIDC provider (only needs to be done once per AWS account)
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### 2. Create IAM Role for GitHub Actions

Create a file `github-actions-role-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_USERNAME/food-diary:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

Replace:
- `YOUR_ACCOUNT_ID` with your AWS account ID
- `YOUR_GITHUB_USERNAME` with your GitHub username or organization name

Create the role:

```bash
# Create the role
aws iam create-role \
  --role-name GitHubActionsDeployRole \
  --assume-role-policy-document file://github-actions-role-policy.json

# Attach required permissions
aws iam attach-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# Note: In production, you should create a custom policy with minimal permissions
# instead of using AdministratorAccess
```

### 3. Configure GitHub Repository Secrets

Go to your GitHub repository:

**Settings → Secrets and variables → Actions**

Add the following **secret**:
- `AWS_ROLE_ARN`: The ARN of the IAM role created above
  - Format: `arn:aws:iam::YOUR_ACCOUNT_ID:role/GitHubActionsDeployRole`

Add the following **variable** (optional):
- `AWS_REGION`: Your target AWS region (default: `us-east-1`)

### 4. Set up GitHub Environment (Optional)

For additional protection:

**Settings → Environments → New environment**

Create an environment named `production` and optionally configure:
- Required reviewers (for manual approval before deployment)
- Deployment branches (restrict to `main` branch only)

### 5. Create AWS Secrets

Before deploying, ensure the OAuth secrets exist:

```bash
just setup-aws-secrets
```

This must be done at least once before the first deployment.

## How It Works

The workflow (`.github/workflows/deploy.yml`) triggers automatically when:
- Code is pushed to the `main` branch (usually via merge)

The workflow:
1. Checks out the code
2. Sets up Python and Node.js
3. Installs AWS CDK
4. Authenticates to AWS using OIDC (no stored credentials!)
5. Verifies that OAuth secrets exist
6. Deploys the CDK stack
7. Uploads static files to S3
8. Posts a deployment summary

## Manual Deployment

You can still deploy manually using:

```bash
just deploy-aws
```

## Troubleshooting

### Workflow fails with "Secret not found"

Run `just setup-aws-secrets` to create the required OAuth secrets in AWS Secrets Manager.

### Workflow fails with "Access Denied"

Check that:
1. The IAM role has sufficient permissions
2. The `AWS_ROLE_ARN` secret is correctly set in GitHub
3. The trust policy includes your repository name

### Workflow fails with "Role not found"

Verify:
1. The IAM role exists: `aws iam get-role --role-name GitHubActionsDeployRole`
2. The role ARN is correct in GitHub secrets

## Security Best Practices

1. **Use OIDC**: This workflow uses OIDC for authentication (no long-lived credentials stored in GitHub)
2. **Minimal permissions**: In production, create a custom IAM policy with only required permissions
3. **Environment protection**: Use GitHub environments with required reviewers for production
4. **Secret rotation**: Regularly rotate OAuth secrets using `just setup-aws-secrets`

## Monitoring

View deployment status:
- **GitHub Actions tab**: See workflow runs and logs
- **AWS CloudWatch**: Monitor Lambda function logs
- **CloudFront**: Check distribution status in AWS console
