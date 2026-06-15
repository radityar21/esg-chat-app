#!/bin/bash
# =============================================================================
# ESG Reporting POC - Complete AWS Account Setup
# Tokaicom Mitra Indonesia (Tokai Group)
# =============================================================================
# INSTRUCTIONS:
#   1. Review and customize REGION if needed (default: ap-southeast-1)
#   2. Run: chmod +x setup_account.sh && ./setup_account.sh
#   3. Script will create: IAM roles, S3 buckets, Lambda functions, Step Functions, API Gateway
# =============================================================================

set -e  # Exit on error

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="ap-southeast-1"  # Singapore region (change if needed)
PROJECT_TAG="Key=Project,Value=ESG Key=Env,Value=Production Key=Owner,Value=TokaiGroup"

echo "========================================="
echo "  ESG Reporting POC - Account Setup"
echo "========================================="
echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"
echo ""

# =============================================================================
# 1. CREATE IAM ROLES
# =============================================================================

echo "📋 Step 1: Creating IAM Roles..."
echo ""

# --- 1a. ESGLambdaExecutionRole (for all 10 Lambda functions) ---
echo "Creating ESGLambdaExecutionRole..."

aws iam create-role \
  --role-name ESGLambdaExecutionRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' \
  --tags Key=Project,Value=ESG Key=Env,Value=Production Key=Owner,Value=TokaiGroup \
  2>/dev/null || echo "  ⚠️  Role already exists, updating policies..."

# Attach basic Lambda execution (CloudWatch Logs)
aws iam attach-role-policy \
  --role-name ESGLambdaExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Custom inline policy for S3, Bedrock, Athena, Glue, Step Functions
aws iam put-role-policy \
  --role-name ESGLambdaExecutionRole \
  --policy-name ESGLambdaCustomPolicy \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Sid\": \"S3Access\",
        \"Effect\": \"Allow\",
        \"Action\": [
          \"s3:GetObject\",
          \"s3:PutObject\",
          \"s3:ListBucket\",
          \"s3:DeleteObject\"
        ],
        \"Resource\": [
          \"arn:aws:s3:::esg-reporting-output-bucket\",
          \"arn:aws:s3:::esg-reporting-output-bucket/*\",
          \"arn:aws:s3:::esg-athena-results\",
          \"arn:aws:s3:::esg-athena-results/*\",
          \"arn:aws:s3:::esg-knowledge-base\",
          \"arn:aws:s3:::esg-knowledge-base/*\"
        ]
      },
      {
        \"Sid\": \"BedrockInvokeModel\",
        \"Effect\": \"Allow\",
        \"Action\": [
          \"bedrock:InvokeModel\",
          \"bedrock:InvokeModelWithResponseStream\"
        ],
        \"Resource\": \"arn:aws:bedrock:${REGION}::foundation-model/anthropic.claude-3-5-sonnet-20240620-v2:0\"
      },
      {
        \"Sid\": \"AthenaAccess\",
        \"Effect\": \"Allow\",
        \"Action\": [
          \"athena:StartQueryExecution\",
          \"athena:GetQueryExecution\",
          \"athena:GetQueryResults\",
          \"athena:StopQueryExecution\"
        ],
        \"Resource\": \"arn:aws:athena:${REGION}:${ACCOUNT_ID}:workgroup/primary\"
      },
      {
        \"Sid\": \"GlueDataCatalogAccess\",
        \"Effect\": \"Allow\",
        \"Action\": [
          \"glue:GetTable\",
          \"glue:GetTables\",
          \"glue:GetDatabase\",
          \"glue:GetDatabases\",
          \"glue:GetPartitions\"
        ],
        \"Resource\": [
          \"arn:aws:glue:${REGION}:${ACCOUNT_ID}:catalog\",
          \"arn:aws:glue:${REGION}:${ACCOUNT_ID}:database/esg_reporting_db\",
          \"arn:aws:glue:${REGION}:${ACCOUNT_ID}:table/esg_reporting_db/*\"
        ]
      },
      {
        \"Sid\": \"StepFunctionsAccess\",
        \"Effect\": \"Allow\",
        \"Action\": [
          \"states:StartExecution\",
          \"states:DescribeExecution\",
          \"states:GetExecutionHistory\",
          \"states:ListExecutions\"
        ],
        \"Resource\": [
          \"arn:aws:states:${REGION}:${ACCOUNT_ID}:stateMachine:esg-orchestrator\",
          \"arn:aws:states:${REGION}:${ACCOUNT_ID}:execution:esg-orchestrator:*\"
        ]
      }
    ]
  }"

echo "  ✅ ESGLambdaExecutionRole created"

# --- 1b. ESGStepFunctionsRole (Step Functions → Lambda invoke) ---
echo "Creating ESGStepFunctionsRole..."

aws iam create-role \
  --role-name ESGStepFunctionsRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "states.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' \
  --tags Key=Project,Value=ESG Key=Env,Value=Production Key=Owner,Value=TokaiGroup \
  2>/dev/null || echo "  ⚠️  Role already exists, updating policies..."

aws iam put-role-policy \
  --role-name ESGStepFunctionsRole \
  --policy-name ESGStepFunctionsPolicy \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Sid\": \"LambdaInvoke\",
        \"Effect\": \"Allow\",
        \"Action\": \"lambda:InvokeFunction\",
        \"Resource\": [
          \"arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:esg-validate-input\",
          \"arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:esg-section-gen\",
          \"arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:esg-filter-sections\",
          \"arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:esg-assembly-doc\",
          \"arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:esg-validation\",
          \"arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:esg-review-handler\"
        ]
      },
      {
        \"Sid\": \"CloudWatchLogs\",
        \"Effect\": \"Allow\",
        \"Action\": [
          \"logs:CreateLogDelivery\",
          \"logs:GetLogDelivery\",
          \"logs:UpdateLogDelivery\",
          \"logs:DeleteLogDelivery\",
          \"logs:ListLogDeliveries\",
          \"logs:PutResourcePolicy\",
          \"logs:DescribeResourcePolicies\",
          \"logs:DescribeLogGroups\"
        ],
        \"Resource\": \"*\"
      }
    ]
  }"

echo "  ✅ ESGStepFunctionsRole created"

# --- 1c. ESGBedrockAgentRole (Bedrock Agent → Lambda, Knowledge Base) ---
echo "Creating ESGBedrockAgentRole..."

aws iam create-role \
  --role-name ESGBedrockAgentRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "bedrock.amazonaws.com"},
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "'${ACCOUNT_ID}'"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:bedrock:'${REGION}':'${ACCOUNT_ID}':agent/*"
        }
      }
    }]
  }' \
  --tags Key=Project,Value=ESG Key=Env,Value=Production Key=Owner,Value=TokaiGroup \
  2>/dev/null || echo "  ⚠️  Role already exists, updating policies..."

aws iam put-role-policy \
  --role-name ESGBedrockAgentRole \
  --policy-name ESGBedrockAgentPolicy \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Sid\": \"BedrockInvokeModel\",
        \"Effect\": \"Allow\",
        \"Action\": \"bedrock:InvokeModel\",
        \"Resource\": \"arn:aws:bedrock:${REGION}::foundation-model/anthropic.claude-3-5-sonnet-20240620-v2:0\"
      },
      {
        \"Sid\": \"BedrockKnowledgeBaseRetrieval\",
        \"Effect\": \"Allow\",
        \"Action\": \"bedrock:Retrieve\",
        \"Resource\": \"arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:knowledge-base/*\"
      },
      {
        \"Sid\": \"LambdaInvokeAgentTools\",
        \"Effect\": \"Allow\",
        \"Action\": \"lambda:InvokeFunction\",
        \"Resource\": \"arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:esg-agent-tools\"
      }
    ]
  }"

echo "  ✅ ESGBedrockAgentRole created"

# =============================================================================
# 2. CREATE S3 BUCKETS
# =============================================================================

echo "📦 Step 2: Creating S3 Buckets..."
echo ""

BUCKETS=(
  "esg-reporting-output-bucket"
  "esg-athena-results"
  "esg-knowledge-base"
)

for BUCKET in "${BUCKETS[@]}"; do
  echo "Creating bucket: $BUCKET"

  # Create bucket (ap-southeast-1 requires LocationConstraint)
  if [ "$REGION" = "us-east-1" ]; then
    aws s3api create-bucket \
      --bucket "$BUCKET" \
      --region "$REGION" \
      2>/dev/null || echo "  ⚠️  Bucket already exists"
  else
    aws s3api create-bucket \
      --bucket "$BUCKET" \
      --region "$REGION" \
      --create-bucket-configuration LocationConstraint="$REGION" \
      2>/dev/null || echo "  ⚠️  Bucket already exists"
  fi

  # Enable versioning
  aws s3api put-bucket-versioning \
    --bucket "$BUCKET" \
    --versioning-configuration Status=Enabled

  # Add tags
  aws s3api put-bucket-tagging \
    --bucket "$BUCKET" \
    --tagging '{
      "TagSet": [
        {"Key": "Project", "Value": "ESG"},
        {"Key": "Env", "Value": "Production"},
        {"Key": "Owner", "Value": "TokaiGroup"}
      ]
    }'

  # Block public access
  aws s3api put-public-access-block \
    --bucket "$BUCKET" \
    --public-access-block-configuration \
      BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

  # Enable encryption (AES-256)
  aws s3api put-bucket-encryption \
    --bucket "$BUCKET" \
    --server-side-encryption-configuration '{
      "Rules": [{
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        }
      }]
    }'

  # Lifecycle: delete old noncurrent versions
  aws s3api put-bucket-lifecycle-configuration \
    --bucket "$BUCKET" \
    --lifecycle-configuration '{
      "Rules": [
        {
          "ID": "DeleteOldVersions",
          "Status": "Enabled",
          "Filter": {},
          "NoncurrentVersionExpiration": {
            "NewerNoncurrentVersions": 3,
            "NoncurrentDays": 30
          }
        }
      ]
    }' 2>/dev/null || true

  echo "  ✅ $BUCKET created"
done

echo ""
echo "✅ All S3 Buckets created successfully!"
echo ""

# =============================================================================
# 3. CREATE FOLDER STRUCTURE IN S3
# =============================================================================

echo "📂 Step 3: Creating folder structure in S3..."
echo ""

REPORTING_YEARS=("2023" "2024")

# Create folders in esg-reporting-output-bucket
for YEAR in "${REPORTING_YEARS[@]}"; do
  aws s3api put-object \
    --bucket "esg-reporting-output-bucket" \
    --key "reports/${YEAR}/" \
    --content-length 0 \
    2>/dev/null || true
done

# Create folders in esg-athena-results
aws s3api put-object \
  --bucket "esg-athena-results" \
  --key "dashboard-cache/" \
  --content-length 0 \
  2>/dev/null || true

aws s3api put-object \
  --bucket "esg-athena-results" \
  --key "queries/" \
  --content-length 0 \
  2>/dev/null || true

# Create folders in esg-knowledge-base
aws s3api put-object \
  --bucket "esg-knowledge-base" \
  --key "documents/" \
  --content-length 0 \
  2>/dev/null || true

echo "  ✅ Folder structure created"
echo ""
echo "✅ S3 Folder structure setup complete!"
echo ""

# --- 1d. ESGAPIGatewayRole (API Gateway → CloudWatch Logs) ---
echo "Creating ESGAPIGatewayRole..."

aws iam create-role \
  --role-name ESGAPIGatewayRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "apigateway.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' \
  --tags Key=Project,Value=ESG Key=Env,Value=Production Key=Owner,Value=TokaiGroup \
  2>/dev/null || echo "  ⚠️  Role already exists, updating policies..."

aws iam attach-role-policy \
  --role-name ESGAPIGatewayRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs

echo "  ✅ ESGAPIGatewayRole created"

# --- 1e. ESGGlueETLRole (Optional: Glue ETL for data pipeline) ---
echo "Creating ESGGlueETLRole (optional)..."

aws iam create-role \
  --role-name ESGGlueETLRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "glue.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' \
  --tags Key=Project,Value=ESG Key=Env,Value=Production Key=Owner,Value=TokaiGroup \
  2>/dev/null || echo "  ⚠️  Role already exists, updating policies..."

aws iam attach-role-policy \
  --role-name ESGGlueETLRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole

aws iam put-role-policy \
  --role-name ESGGlueETLRole \
  --policy-name ESGGlueS3Access \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Effect\": \"Allow\",
        \"Action\": [
          \"s3:GetObject\",
          \"s3:PutObject\",
          \"s3:DeleteObject\",
          \"s3:ListBucket\"
        ],
        \"Resource\": [
          \"arn:aws:s3:::esg-reporting-output-bucket\",
          \"arn:aws:s3:::esg-reporting-output-bucket/*\",
          \"arn:aws:s3:::esg-athena-results\",
          \"arn:aws:s3:::esg-athena-results/*\"
        ]
      }
    ]
  }"

echo "  ✅ ESGGlueETLRole created"
echo ""
echo "✅ All IAM Roles created successfully!"
echo ""

# =============================================================================
# 4. CREATE GLUE DATA CATALOG (Database)
# =============================================================================

echo "🗄️  Step 4: Creating Glue Data Catalog..."
echo ""

aws glue create-database \
  --database-input "{
    \"Name\": \"esg_reporting_db\",
    \"Description\": \"ESG Reporting Database for Athena queries\",
    \"LocationUri\": \"s3://esg-athena-results/\",
    \"Parameters\": {
      \"Project\": \"ESG\",
      \"Owner\": \"TokaiGroup\"
    }
  }" \
  --region "$REGION" \
  2>/dev/null || echo "  ⚠️  Database already exists"

echo "  ✅ Glue database 'esg_reporting_db' created"
echo ""
echo "✅ Glue Data Catalog setup complete!"
echo ""

# =============================================================================
# 5. SUMMARY
# =============================================================================

echo ""
echo "========================================="
echo "  🎉 SETUP COMPLETE!"
echo "========================================="
echo ""
echo "✅ IAM Roles created:"
echo "   - ESGLambdaExecutionRole (for 10 Lambda functions)"
echo "   - ESGStepFunctionsRole (for Step Functions orchestrator)"
echo "   - ESGBedrockAgentRole (for Bedrock Agent)"
echo "   - ESGAPIGatewayRole (for API Gateway logging)"
echo "   - ESGGlueETLRole (optional, for Glue ETL)"
echo ""
echo "✅ S3 Buckets created:"
echo "   - esg-reporting-output-bucket (DOCX/PPTX reports)"
echo "   - esg-athena-results (Athena query results + dashboard cache)"
echo "   - esg-knowledge-base (ESG framework documents)"
echo ""
echo "✅ Glue Database created:"
echo "   - esg_reporting_db"
echo ""
echo "========================================="
echo "  NEXT STEPS:"
echo "========================================="
echo ""
echo "1. Deploy Lambda functions:"
echo "   cd ../lambda"
echo "   ./deploy_all_lambdas.sh"
echo ""
echo "2. Deploy Step Functions:"
echo "   cd ../step_functions"
echo "   aws stepfunctions create-state-machine --cli-input-json file://create_state_machine.json"
echo ""
echo "3. Setup Bedrock Agent:"
echo "   cd ../agent"
echo "   # Follow agent/README.md for setup instructions"
echo ""
echo "4. Deploy API Gateway:"
echo "   # Follow esg-reporting-poc/README.md for API Gateway setup"
echo ""
echo "5. Deploy Frontend to Amplify:"
echo "   cd ../../esg-chat-app-react"
echo "   git push origin main  # Amplify auto-deploys from GitHub"
echo ""
echo "========================================="
echo "  📚 Documentation:"
echo "========================================="
echo ""
echo "- Root README: ../../README.md"
echo "- Backend README: ../README.md"
echo "- Lambda README: ../lambda/README.md"
echo "- Agent README: ../agent/README.md"
echo "- Frontend README: ../../esg-chat-app-react/README.md"
echo "- Architecture: ../../architecture/README.md"
echo ""
echo "========================================="
echo ""
echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"
echo ""
echo "Happy building! 🚀"
echo ""
