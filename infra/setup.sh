#!/usr/bin/env bash
# One-time AWS infrastructure setup for LocationsBook backend
# Usage: ./infra/setup.sh
#
# Prerequisites:
#   - AWS CLI v2 configured with admin credentials
#   - Docker running (for initial image build/push)
#   - jq installed
#
# This script is idempotent where possible — re-running will skip resources
# that already exist.

set -euo pipefail

###############################################################################
# Configuration
###############################################################################
APP_NAME="locationsbook"
SERVICE_NAME="lb-backend"
AWS_REGION="${AWS_REGION:-us-east-1}"
GITHUB_REPO="jlucas91/lb-backend"

# RDS
DB_NAME="locationsbook"
DB_USER="locationsbook"
DB_INSTANCE_CLASS="db.t4g.micro"
DB_STORAGE=20
DB_ENGINE_VERSION="16.4"

# Networking
VPC_CIDR="10.0.0.0/16"
SUBNET_A_CIDR="10.0.1.0/24"
SUBNET_B_CIDR="10.0.2.0/24"
AZ_A="${AWS_REGION}a"
AZ_B="${AWS_REGION}b"

# App Runner
APP_PORT=9000

echo "==> Setting up ${APP_NAME} infrastructure in ${AWS_REGION}"
echo ""

###############################################################################
# Helper
###############################################################################
aws_() { aws --region "$AWS_REGION" "$@"; }

###############################################################################
# 1. ECR Repository
###############################################################################
echo "--- 1. ECR Repository ---"
ECR_REPO="${APP_NAME}/${SERVICE_NAME}"

if aws_ ecr describe-repositories --repository-names "$ECR_REPO" &>/dev/null; then
  echo "ECR repo ${ECR_REPO} already exists."
else
  aws_ ecr create-repository \
    --repository-name "$ECR_REPO" \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256
  echo "Created ECR repo: ${ECR_REPO}"
fi

# Lifecycle policy: keep last 10 images
aws_ ecr put-lifecycle-policy \
  --repository-name "$ECR_REPO" \
  --lifecycle-policy-text '{
    "rules": [{
      "rulePriority": 1,
      "description": "Keep last 10 images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": { "type": "expire" }
    }]
  }'

ECR_URI=$(aws_ ecr describe-repositories --repository-names "$ECR_REPO" \
  --query 'repositories[0].repositoryUri' --output text)
AWS_ACCOUNT_ID=$(aws_ sts get-caller-identity --query Account --output text)
echo "ECR URI: ${ECR_URI}"
echo ""

###############################################################################
# 2. VPC
###############################################################################
echo "--- 2. VPC ---"
VPC_ID=$(aws_ ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=${APP_NAME}-vpc" \
  --query 'Vpcs[0].VpcId' --output text 2>/dev/null || echo "None")

if [ "$VPC_ID" = "None" ] || [ -z "$VPC_ID" ]; then
  VPC_ID=$(aws_ ec2 create-vpc --cidr-block "$VPC_CIDR" \
    --query 'Vpc.VpcId' --output text)
  aws_ ec2 create-tags --resources "$VPC_ID" \
    --tags "Key=Name,Value=${APP_NAME}-vpc"
  aws_ ec2 modify-vpc-attribute --vpc-id "$VPC_ID" --enable-dns-support
  aws_ ec2 modify-vpc-attribute --vpc-id "$VPC_ID" --enable-dns-hostnames
  echo "Created VPC: ${VPC_ID}"
else
  echo "VPC already exists: ${VPC_ID}"
fi
echo ""

###############################################################################
# 3. Private Subnets
###############################################################################
echo "--- 3. Private Subnets ---"

create_subnet() {
  local name=$1 cidr=$2 az=$3
  local subnet_id
  subnet_id=$(aws_ ec2 describe-subnets \
    --filters "Name=tag:Name,Values=${name}" "Name=vpc-id,Values=${VPC_ID}" \
    --query 'Subnets[0].SubnetId' --output text 2>/dev/null || echo "None")

  if [ "$subnet_id" = "None" ] || [ -z "$subnet_id" ]; then
    subnet_id=$(aws_ ec2 create-subnet \
      --vpc-id "$VPC_ID" --cidr-block "$cidr" --availability-zone "$az" \
      --query 'Subnet.SubnetId' --output text)
    aws_ ec2 create-tags --resources "$subnet_id" \
      --tags "Key=Name,Value=${name}"
    echo "Created subnet ${name}: ${subnet_id}"
  else
    echo "Subnet ${name} already exists: ${subnet_id}"
  fi
  echo "$subnet_id"
}

SUBNET_A_ID=$(create_subnet "${APP_NAME}-private-a" "$SUBNET_A_CIDR" "$AZ_A" | tail -1)
SUBNET_B_ID=$(create_subnet "${APP_NAME}-private-b" "$SUBNET_B_CIDR" "$AZ_B" | tail -1)
echo ""

###############################################################################
# 4. Security Groups
###############################################################################
echo "--- 4. Security Groups ---"

get_or_create_sg() {
  local name=$1 desc=$2
  local sg_id
  sg_id=$(aws_ ec2 describe-security-groups \
    --filters "Name=group-name,Values=${name}" "Name=vpc-id,Values=${VPC_ID}" \
    --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "None")

  if [ "$sg_id" = "None" ] || [ -z "$sg_id" ]; then
    sg_id=$(aws_ ec2 create-security-group \
      --group-name "$name" --description "$desc" --vpc-id "$VPC_ID" \
      --query 'GroupId' --output text)
    echo "Created SG ${name}: ${sg_id}" >&2
  else
    echo "SG ${name} already exists: ${sg_id}" >&2
  fi
  echo "$sg_id"
}

APPRUNNER_SG_ID=$(get_or_create_sg "${APP_NAME}-apprunner-sg" "App Runner VPC connector")
RDS_SG_ID=$(get_or_create_sg "${APP_NAME}-rds-sg" "RDS PostgreSQL")

# Allow RDS SG inbound on 5432 from App Runner SG (idempotent — ignore duplicate errors)
aws_ ec2 authorize-security-group-ingress \
  --group-id "$RDS_SG_ID" \
  --protocol tcp --port 5432 \
  --source-group "$APPRUNNER_SG_ID" 2>/dev/null || true

echo "App Runner SG: ${APPRUNNER_SG_ID}"
echo "RDS SG: ${RDS_SG_ID}"
echo ""

###############################################################################
# 5. RDS Subnet Group + Instance
###############################################################################
echo "--- 5. RDS PostgreSQL ---"

# Subnet group
if ! aws_ rds describe-db-subnet-groups \
    --db-subnet-group-name "${APP_NAME}-db-subnet" &>/dev/null; then
  aws_ rds create-db-subnet-group \
    --db-subnet-group-name "${APP_NAME}-db-subnet" \
    --db-subnet-group-description "Private subnets for ${APP_NAME} RDS" \
    --subnet-ids "$SUBNET_A_ID" "$SUBNET_B_ID"
  echo "Created DB subnet group."
else
  echo "DB subnet group already exists."
fi

# Generate DB password
DB_PASSWORD=$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 32)

# RDS instance
if aws_ rds describe-db-instances \
    --db-instance-identifier "${APP_NAME}-db" &>/dev/null; then
  echo "RDS instance already exists."
  # Retrieve existing endpoint
  RDS_ENDPOINT=$(aws_ rds describe-db-instances \
    --db-instance-identifier "${APP_NAME}-db" \
    --query 'DBInstances[0].Endpoint.Address' --output text)
  echo "Note: Using existing DB. Password was NOT changed."
  echo "  If you need the DATABASE_URL, retrieve it from Secrets Manager."
  DB_PASSWORD="<existing — check Secrets Manager>"
else
  aws_ rds create-db-instance \
    --db-instance-identifier "${APP_NAME}-db" \
    --db-instance-class "$DB_INSTANCE_CLASS" \
    --engine postgres \
    --engine-version "$DB_ENGINE_VERSION" \
    --master-username "$DB_USER" \
    --master-user-password "$DB_PASSWORD" \
    --db-name "$DB_NAME" \
    --allocated-storage "$DB_STORAGE" \
    --storage-type gp3 \
    --storage-encrypted \
    --vpc-security-group-ids "$RDS_SG_ID" \
    --db-subnet-group-name "${APP_NAME}-db-subnet" \
    --no-publicly-accessible \
    --deletion-protection \
    --backup-retention-period 7 \
    --no-multi-az \
    --tags "Key=app,Value=${APP_NAME}"

  echo "Waiting for RDS instance to become available (this takes ~5-10 min)..."
  aws_ rds wait db-instance-available \
    --db-instance-identifier "${APP_NAME}-db"

  RDS_ENDPOINT=$(aws_ rds describe-db-instances \
    --db-instance-identifier "${APP_NAME}-db" \
    --query 'DBInstances[0].Endpoint.Address' --output text)
  echo "RDS endpoint: ${RDS_ENDPOINT}"
fi

DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${RDS_ENDPOINT}:5432/${DB_NAME}"
echo ""

###############################################################################
# 6. Secrets Manager
###############################################################################
echo "--- 6. Secrets Manager ---"
SECRET_KEY=$(openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c 64)

SECRET_ARN=$(aws_ secretsmanager describe-secret \
  --secret-id "${APP_NAME}/backend" \
  --query 'ARN' --output text 2>/dev/null || echo "None")

if [ "$SECRET_ARN" = "None" ] || [ -z "$SECRET_ARN" ]; then
  SECRET_ARN=$(aws_ secretsmanager create-secret \
    --name "${APP_NAME}/backend" \
    --description "LocationsBook backend secrets" \
    --secret-string "$(jq -n \
      --arg db_url "$DATABASE_URL" \
      --arg secret_key "$SECRET_KEY" \
      --arg db_password "$DB_PASSWORD" \
      '{DATABASE_URL: $db_url, SECRET_KEY: $secret_key, DB_PASSWORD: $db_password}')" \
    --query 'ARN' --output text)
  echo "Created secret: ${SECRET_ARN}"
else
  echo "Secret already exists: ${SECRET_ARN}"
  echo "  Updating secret values..."
  aws_ secretsmanager put-secret-value \
    --secret-id "${APP_NAME}/backend" \
    --secret-string "$(jq -n \
      --arg db_url "$DATABASE_URL" \
      --arg secret_key "$SECRET_KEY" \
      --arg db_password "$DB_PASSWORD" \
      '{DATABASE_URL: $db_url, SECRET_KEY: $secret_key, DB_PASSWORD: $db_password}')"
fi
echo ""

###############################################################################
# 7. IAM Roles
###############################################################################
echo "--- 7. IAM Roles ---"

# App Runner ECR access role
ECR_ACCESS_ROLE_NAME="${APP_NAME}-apprunner-ecr-access"
if ! aws_ iam get-role --role-name "$ECR_ACCESS_ROLE_NAME" &>/dev/null; then
  aws_ iam create-role \
    --role-name "$ECR_ACCESS_ROLE_NAME" \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": { "Service": "build.apprunner.amazonaws.com" },
        "Action": "sts:AssumeRole"
      }]
    }'
  aws_ iam attach-role-policy \
    --role-name "$ECR_ACCESS_ROLE_NAME" \
    --policy-arn "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
  echo "Created ECR access role."
else
  echo "ECR access role already exists."
fi
ECR_ACCESS_ROLE_ARN=$(aws_ iam get-role --role-name "$ECR_ACCESS_ROLE_NAME" \
  --query 'Role.Arn' --output text)

# App Runner instance role (for Secrets Manager access)
INSTANCE_ROLE_NAME="${APP_NAME}-apprunner-instance"
if ! aws_ iam get-role --role-name "$INSTANCE_ROLE_NAME" &>/dev/null; then
  aws_ iam create-role \
    --role-name "$INSTANCE_ROLE_NAME" \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": { "Service": "tasks.apprunner.amazonaws.com" },
        "Action": "sts:AssumeRole"
      }]
    }'

  aws_ iam put-role-policy \
    --role-name "$INSTANCE_ROLE_NAME" \
    --policy-name "secrets-access" \
    --policy-document "$(jq -n \
      --arg secret_arn "$SECRET_ARN" \
      '{
        Version: "2012-10-17",
        Statement: [{
          Effect: "Allow",
          Action: ["secretsmanager:GetSecretValue"],
          Resource: $secret_arn
        }]
      }')"
  echo "Created instance role with Secrets Manager access."
else
  echo "Instance role already exists."
fi
INSTANCE_ROLE_ARN=$(aws_ iam get-role --role-name "$INSTANCE_ROLE_NAME" \
  --query 'Role.Arn' --output text)

# ECS task execution role (for Fargate migrations)
ECS_EXEC_ROLE_NAME="${APP_NAME}-ecs-execution"
if ! aws_ iam get-role --role-name "$ECS_EXEC_ROLE_NAME" &>/dev/null; then
  aws_ iam create-role \
    --role-name "$ECS_EXEC_ROLE_NAME" \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": { "Service": "ecs-tasks.amazonaws.com" },
        "Action": "sts:AssumeRole"
      }]
    }'
  aws_ iam attach-role-policy \
    --role-name "$ECS_EXEC_ROLE_NAME" \
    --policy-arn "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
  echo "Created ECS execution role."
else
  echo "ECS execution role already exists."
fi
ECS_EXEC_ROLE_ARN=$(aws_ iam get-role --role-name "$ECS_EXEC_ROLE_NAME" \
  --query 'Role.Arn' --output text)

# ECS task role (for the migration container itself — needs Secrets Manager)
ECS_TASK_ROLE_NAME="${APP_NAME}-ecs-task"
if ! aws_ iam get-role --role-name "$ECS_TASK_ROLE_NAME" &>/dev/null; then
  aws_ iam create-role \
    --role-name "$ECS_TASK_ROLE_NAME" \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": { "Service": "ecs-tasks.amazonaws.com" },
        "Action": "sts:AssumeRole"
      }]
    }'
  echo "Created ECS task role."
else
  echo "ECS task role already exists."
fi
ECS_TASK_ROLE_ARN=$(aws_ iam get-role --role-name "$ECS_TASK_ROLE_NAME" \
  --query 'Role.Arn' --output text)

echo "ECR access role ARN: ${ECR_ACCESS_ROLE_ARN}"
echo "Instance role ARN: ${INSTANCE_ROLE_ARN}"
echo "ECS execution role ARN: ${ECS_EXEC_ROLE_ARN}"
echo "ECS task role ARN: ${ECS_TASK_ROLE_ARN}"
echo ""

###############################################################################
# 8. VPC Connector
###############################################################################
echo "--- 8. VPC Connector ---"

VPC_CONNECTOR_ARN=$(aws_ apprunner list-vpc-connectors \
  --query "VpcConnectors[?VpcConnectorName=='${APP_NAME}-vpc-connector'] | [0].VpcConnectorArn" \
  --output text 2>/dev/null || echo "None")

if [ "$VPC_CONNECTOR_ARN" = "None" ] || [ -z "$VPC_CONNECTOR_ARN" ]; then
  VPC_CONNECTOR_ARN=$(aws_ apprunner create-vpc-connector \
    --vpc-connector-name "${APP_NAME}-vpc-connector" \
    --subnets "$SUBNET_A_ID" "$SUBNET_B_ID" \
    --security-groups "$APPRUNNER_SG_ID" \
    --query 'VpcConnector.VpcConnectorArn' --output text)
  echo "Created VPC Connector: ${VPC_CONNECTOR_ARN}"
else
  echo "VPC Connector already exists: ${VPC_CONNECTOR_ARN}"
fi
echo ""

###############################################################################
# 9. Build & Push Initial Docker Image
###############################################################################
echo "--- 9. Build & Push Docker Image ---"

aws_ ecr get-login-password | docker login --username AWS --password-stdin \
  "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

IMAGE_TAG="${ECR_URI}:latest"
docker build -t "$IMAGE_TAG" .
docker push "$IMAGE_TAG"
echo "Pushed: ${IMAGE_TAG}"
echo ""

###############################################################################
# 10. App Runner Service
###############################################################################
echo "--- 10. App Runner Service ---"

# Wait for IAM role propagation
echo "Waiting 10s for IAM role propagation..."
sleep 10

APPRUNNER_SERVICE_ARN=$(aws_ apprunner list-services \
  --query "ServiceSummaryList[?ServiceName=='${SERVICE_NAME}'] | [0].ServiceArn" \
  --output text 2>/dev/null || echo "None")

if [ "$APPRUNNER_SERVICE_ARN" = "None" ] || [ -z "$APPRUNNER_SERVICE_ARN" ]; then
  APPRUNNER_SERVICE_ARN=$(aws_ apprunner create-service \
    --service-name "$SERVICE_NAME" \
    --source-configuration "{
      \"AuthenticationConfiguration\": {
        \"AccessRoleArn\": \"${ECR_ACCESS_ROLE_ARN}\"
      },
      \"ImageRepository\": {
        \"ImageIdentifier\": \"${IMAGE_TAG}\",
        \"ImageRepositoryType\": \"ECR\",
        \"ImageConfiguration\": {
          \"Port\": \"${APP_PORT}\",
          \"RuntimeEnvironmentVariables\": {
            \"DATABASE_URL\": \"${DATABASE_URL}\",
            \"SECRET_KEY\": \"${SECRET_KEY}\",
            \"APP_ENV\": \"production\"
          }
        }
      },
      \"AutoDeploymentsEnabled\": false
    }" \
    --instance-configuration "{
      \"Cpu\": \"1024\",
      \"Memory\": \"2048\",
      \"InstanceRoleArn\": \"${INSTANCE_ROLE_ARN}\"
    }" \
    --health-check-configuration "{
      \"Protocol\": \"HTTP\",
      \"Path\": \"/api/v1/health\",
      \"Interval\": 10,
      \"Timeout\": 5,
      \"HealthyThreshold\": 1,
      \"UnhealthyThreshold\": 5
    }" \
    --network-configuration "{
      \"EgressConfiguration\": {
        \"EgressType\": \"VPC\",
        \"VpcConnectorArn\": \"${VPC_CONNECTOR_ARN}\"
      }
    }" \
    --query 'Service.ServiceArn' --output text)

  echo "Creating App Runner service (this takes ~3-5 min)..."
  aws_ apprunner wait service-running \
    --service-arn "$APPRUNNER_SERVICE_ARN" 2>/dev/null || \
    echo "  (wait command may not exist — check console for status)"

  echo "App Runner service ARN: ${APPRUNNER_SERVICE_ARN}"
else
  echo "App Runner service already exists: ${APPRUNNER_SERVICE_ARN}"
fi

APPRUNNER_URL=$(aws_ apprunner describe-service \
  --service-arn "$APPRUNNER_SERVICE_ARN" \
  --query 'Service.ServiceUrl' --output text)
echo "App Runner URL: https://${APPRUNNER_URL}"
echo ""

###############################################################################
# 11. ECS Cluster + Task Definition (for Alembic migrations)
###############################################################################
echo "--- 11. ECS Cluster + Migration Task Definition ---"

# Cluster
if ! aws_ ecs describe-clusters --clusters "${APP_NAME}-migrations" \
    --query 'clusters[?status==`ACTIVE`] | [0].clusterArn' --output text 2>/dev/null | grep -q arn; then
  aws_ ecs create-cluster --cluster-name "${APP_NAME}-migrations"
  echo "Created ECS cluster: ${APP_NAME}-migrations"
else
  echo "ECS cluster already exists."
fi

# CloudWatch log group for migrations
aws_ logs create-log-group \
  --log-group-name "/ecs/${APP_NAME}-migrate" 2>/dev/null || true

# Task definition
aws_ ecs register-task-definition \
  --family "${APP_NAME}-migrate" \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu "256" \
  --memory "512" \
  --execution-role-arn "$ECS_EXEC_ROLE_ARN" \
  --task-role-arn "$ECS_TASK_ROLE_ARN" \
  --container-definitions "[{
    \"name\": \"migrate\",
    \"image\": \"${IMAGE_TAG}\",
    \"essential\": true,
    \"command\": [\"alembic\", \"upgrade\", \"head\"],
    \"environment\": [
      {\"name\": \"DATABASE_URL\", \"value\": \"${DATABASE_URL}\"},
      {\"name\": \"SECRET_KEY\", \"value\": \"${SECRET_KEY}\"}
    ],
    \"logConfiguration\": {
      \"logDriver\": \"awslogs\",
      \"options\": {
        \"awslogs-group\": \"/ecs/${APP_NAME}-migrate\",
        \"awslogs-region\": \"${AWS_REGION}\",
        \"awslogs-stream-prefix\": \"migrate\"
      }
    }
  }]"
echo "Registered migration task definition."
echo ""

###############################################################################
# 12. GitHub OIDC Role
###############################################################################
echo "--- 12. GitHub OIDC Role ---"

# Create OIDC provider if it doesn't exist
OIDC_PROVIDER_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
if ! aws_ iam get-open-id-connect-provider \
    --open-id-connect-provider-arn "$OIDC_PROVIDER_ARN" &>/dev/null; then
  # Get GitHub's OIDC thumbprint
  THUMBPRINT=$(openssl s_client -servername token.actions.githubusercontent.com \
    -showcerts -connect token.actions.githubusercontent.com:443 </dev/null 2>/dev/null | \
    openssl x509 -fingerprint -noout 2>/dev/null | \
    sed 's/://g' | cut -d= -f2 | tr '[:upper:]' '[:lower:]')

  aws_ iam create-open-id-connect-provider \
    --url "https://token.actions.githubusercontent.com" \
    --client-id-list "sts.amazonaws.com" \
    --thumbprint-list "${THUMBPRINT:-6938fd4d98bab03faadb97b34396831e3780aea1}"
  echo "Created GitHub OIDC provider."
else
  echo "GitHub OIDC provider already exists."
fi

GITHUB_DEPLOY_ROLE_NAME="${APP_NAME}-github-deploy"
if ! aws_ iam get-role --role-name "$GITHUB_DEPLOY_ROLE_NAME" &>/dev/null; then
  aws_ iam create-role \
    --role-name "$GITHUB_DEPLOY_ROLE_NAME" \
    --assume-role-policy-document "$(jq -n \
      --arg account_id "$AWS_ACCOUNT_ID" \
      --arg repo "$GITHUB_REPO" \
      '{
        Version: "2012-10-17",
        Statement: [{
          Effect: "Allow",
          Principal: {
            Federated: "arn:aws:iam::\($account_id):oidc-provider/token.actions.githubusercontent.com"
          },
          Action: "sts:AssumeRoleWithWebIdentity",
          Condition: {
            StringEquals: {
              "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
            },
            StringLike: {
              "token.actions.githubusercontent.com:sub": "repo:\($repo):ref:refs/heads/main"
            }
          }
        }]
      }')"

  # Inline policy for deploy permissions
  aws_ iam put-role-policy \
    --role-name "$GITHUB_DEPLOY_ROLE_NAME" \
    --policy-name "deploy" \
    --policy-document "$(jq -n \
      --arg ecr_repo_arn "arn:aws:ecr:${AWS_REGION}:${AWS_ACCOUNT_ID}:repository/${ECR_REPO}" \
      --arg apprunner_arn "$APPRUNNER_SERVICE_ARN" \
      --arg cluster_arn "arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:cluster/${APP_NAME}-migrations" \
      --arg task_def_arn "arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:task-definition/${APP_NAME}-migrate:*" \
      --arg exec_role_arn "$ECS_EXEC_ROLE_ARN" \
      --arg task_role_arn "$ECS_TASK_ROLE_ARN" \
      --arg log_group_arn "arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:/ecs/${APP_NAME}-migrate:*" \
      '{
        Version: "2012-10-17",
        Statement: [
          {
            Sid: "ECRAuth",
            Effect: "Allow",
            Action: "ecr:GetAuthorizationToken",
            Resource: "*"
          },
          {
            Sid: "ECRPush",
            Effect: "Allow",
            Action: [
              "ecr:BatchCheckLayerAvailability",
              "ecr:GetDownloadUrlForLayer",
              "ecr:BatchGetImage",
              "ecr:PutImage",
              "ecr:InitiateLayerUpload",
              "ecr:UploadLayerPart",
              "ecr:CompleteLayerUpload"
            ],
            Resource: $ecr_repo_arn
          },
          {
            Sid: "AppRunner",
            Effect: "Allow",
            Action: [
              "apprunner:UpdateService",
              "apprunner:DescribeService"
            ],
            Resource: $apprunner_arn
          },
          {
            Sid: "ECSMigrate",
            Effect: "Allow",
            Action: [
              "ecs:RunTask",
              "ecs:DescribeTasks",
              "ecs:RegisterTaskDefinition"
            ],
            Resource: [$cluster_arn, $task_def_arn]
          },
          {
            Sid: "ECSRunTask",
            Effect: "Allow",
            Action: "ecs:RunTask",
            Resource: $task_def_arn,
            Condition: {
              "ArnEquals": {
                "ecs:cluster": $cluster_arn
              }
            }
          },
          {
            Sid: "PassRole",
            Effect: "Allow",
            Action: "iam:PassRole",
            Resource: [$exec_role_arn, $task_role_arn]
          },
          {
            Sid: "Logs",
            Effect: "Allow",
            Action: [
              "logs:GetLogEvents",
              "logs:DescribeLogStreams"
            ],
            Resource: $log_group_arn
          }
        ]
      }')"
  echo "Created GitHub deploy role."
else
  echo "GitHub deploy role already exists."
fi
GITHUB_DEPLOY_ROLE_ARN=$(aws_ iam get-role --role-name "$GITHUB_DEPLOY_ROLE_NAME" \
  --query 'Role.Arn' --output text)
echo ""

###############################################################################
# Summary
###############################################################################
echo ""
echo "==========================================================================="
echo "  SETUP COMPLETE"
echo "==========================================================================="
echo ""
echo "App Runner URL:    https://${APPRUNNER_URL}"
echo ""
echo "--- GitHub Repository Secrets to Configure ---"
echo ""
echo "  AWS_DEPLOY_ROLE_ARN:       ${GITHUB_DEPLOY_ROLE_ARN}"
echo "  APPRUNNER_SERVICE_ARN:     ${APPRUNNER_SERVICE_ARN}"
echo "  APPRUNNER_ACCESS_ROLE_ARN: ${ECR_ACCESS_ROLE_ARN}"
echo "  ECR_REPO_URI:              ${ECR_URI}"
echo "  DATABASE_URL:              ${DATABASE_URL}"
echo "  SECRET_KEY:                ${SECRET_KEY}"
echo "  PRIVATE_SUBNET_IDS:        ${SUBNET_A_ID},${SUBNET_B_ID}"
echo "  APPRUNNER_SG_ID:           ${APPRUNNER_SG_ID}"
echo "  ECS_EXEC_ROLE_ARN:         ${ECS_EXEC_ROLE_ARN}"
echo "  ECS_TASK_ROLE_ARN:         ${ECS_TASK_ROLE_ARN}"
echo ""
echo "--- Run Alembic migration ---"
echo "  aws ecs run-task \\"
echo "    --cluster ${APP_NAME}-migrations \\"
echo "    --task-definition ${APP_NAME}-migrate \\"
echo "    --launch-type FARGATE \\"
echo "    --network-configuration '{\"awsvpcConfiguration\":{\"subnets\":[\"${SUBNET_A_ID}\",\"${SUBNET_B_ID}\"],\"securityGroups\":[\"${APPRUNNER_SG_ID}\"]}}'"
echo ""
echo "--- Verify ---"
echo "  curl https://${APPRUNNER_URL}/api/v1/health"
echo "==========================================================================="
