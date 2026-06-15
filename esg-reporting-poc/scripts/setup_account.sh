#!/bin/bash
# =============================================================================
# D1: AWS Account Setup & IAM
# ESG Reporting POC - Manual AWS CLI Commands
# =============================================================================
# INSTRUCTIONS:
#   1. Replace ACCOUNT_ID with your actual AWS account ID
#   2. Set your preferred region
#   3. Run commands sequentially
# =============================================================================

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
PROJECT_TAG="Key=Project,Value=ESG Key=Env,Value=POC Key=Team,Value=Sustainability"

echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"

# =============================================================================
# 1. CREATE IAM ROLES
# =============================================================================

# --- 1a. ESGGlueRole (Glue → S3 read/write, CloudWatch logs) ---

aws iam create-role \
  --role-name ESGGlueRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "glue.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' \
  --tags Key=Project,Value=ESG Key=Env,Value=POC Key=Team,Value=Sustainability

aws iam attach-role-policy \
  --role-name ESGGlueRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole

aws iam put-role-policy \
  --role-name ESGGlueRole \
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
          \"arn:aws:s3:::esg-data-raw-${ACCOUNT_ID}\",
          \"arn:aws:s3:::esg-data-raw-${ACCOUNT_ID}/*\",
          \"arn:aws:s3:::esg-data-curated-${ACCOUNT_ID}\",
          \"arn:aws:s3:::esg-data-curated-${ACCOUNT_ID}/*\",
          \"arn:aws:s3:::esg-data-aggregated-${ACCOUNT_ID}\",
          \"arn:aws:s3:::esg-data-aggregated-${ACCOUNT_ID}/*\"
        ]
      },
      {
        \"Effect\": \"Allow\",
        \"Action\": [
          \"logs:CreateLogGroup\",
          \"logs:CreateLogStream\",
          \"logs:PutLogEvents\"
        ],
        \"Resource\": \"arn:aws:logs:${REGION}:${ACCOUNT_ID}:*\"
      }
    ]
  }"

# --- 1b. ESGLambdaRole (Lambda → S3, Athena, Bedrock, DynamoDB, CloudWatch) ---

aws iam create-role \
  --role-name ESGLambdaRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' \
  --tags Key=Project,Value=ESG Key=Env,Value=POC Key=Team,Value=Sustainability

aws iam attach-role-policy \
  --role-name ESGLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam put-role-policy \
  --role-name ESGLambdaRole \
  --policy-name ESGLambdaAccess \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Sid\": \"S3Access\",
        \"Effect\": \"Allow\",
        \"Action\": [
          \"s3:GetObject\",
          \"s3:PutObject\",
          \"s3:ListBucket\"
        ],
        \"Resource\": [
          \"arn:aws:s3:::esg-data-raw-${ACCOUNT_ID}\",
          \"arn:aws:s3:::esg-data-raw-${ACCOUNT_ID}/*\",
          \"arn:aws:s3:::esg-data-curated-${ACCOUNT_ID}\",
          \"arn:aws:s3:::esg-data-curated-${ACCOUNT_ID}/*\",
          \"arn:aws:s3:::esg-data-aggregated-${ACCOUNT_ID}\",
          \"arn:aws:s3:::esg-data-aggregated-${ACCOUNT_ID}/*\",
          \"arn:aws:s3:::esg-output-reports-${ACCOUNT_ID}\",
          \"arn:aws:s3:::esg-output-reports-${ACCOUNT_ID}/*\"
        ]
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
        \"Resource\": \"arn:aws:athena:${REGION}:${ACCOUNT_ID}:workgroup/*\"
      },
      {
        \"Sid\": \"GlueAccess\",
        \"Effect\": \"Allow\",
        \"Action\": [
          \"glue:GetTable\",
          \"glue:GetTables\",
          \"glue:GetDatabase\",
          \"glue:GetDatabases\",
          \"glue:GetPartitions\"
        ],
        \"Resource\": \"*\"
      },
      {
        \"Sid\": \"BedrockAccess\",
        \"Effect\": \"Allow\",
        \"Action\": [
          \"bedrock:InvokeModel\",
          \"bedrock:InvokeModelWithResponseStream\"
        ],
        \"Resource\": \"arn:aws:bedrock:us-east-1::foundation-model/*\"
      },
      {
        \"Sid\": \"BedrockKBAccess\",
        \"Effect\": \"Allow\",
        \"Action\": [
          \"bedrock:Retrieve\",
          \"bedrock:RetrieveAndGenerate\"
        ],
        \"Resource\": \"arn:aws:bedrock:us-east-1:${ACCOUNT_ID}:knowledge-base/*\"
      },
      {
        \"Sid\": \"DynamoDBAccess\",
        \"Effect\": \"Allow\",
        \"Action\": [
          \"dynamodb:PutItem\",
          \"dynamodb:GetItem\",
          \"dynamodb:UpdateItem\",
          \"dynamodb:Query\",
          \"dynamodb:Scan\"
        ],
        \"Resource\": \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/ESG*\"
      }
    ]
  }"

# --- 1c. ESGStepFunctionsRole (StepFunctions → Lambda invoke, SNS publish) ---

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
  --tags Key=Project,Value=ESG Key=Env,Value=POC Key=Team,Value=Sustainability

aws iam put-role-policy \
  --role-name ESGStepFunctionsRole \
  --policy-name ESGStepFunctionsAccess \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Sid\": \"LambdaInvoke\",
        \"Effect\": \"Allow\",
        \"Action\": [
          \"lambda:InvokeFunction\"
        ],
        \"Resource\": \"arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:esg-*\"
      },
      {
        \"Sid\": \"SNSPublish\",
        \"Effect\": \"Allow\",
        \"Action\": [
          \"sns:Publish\"
        ],
        \"Resource\": \"arn:aws:sns:${REGION}:${ACCOUNT_ID}:ESG*\"
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

echo "✅ IAM Roles created successfully"

# =============================================================================
# 2. CREATE S3 BUCKETS
# =============================================================================

BUCKETS=(
  "esg-data-raw-${ACCOUNT_ID}"
  "esg-data-curated-${ACCOUNT_ID}"
  "esg-data-aggregated-${ACCOUNT_ID}"
  "esg-output-reports-${ACCOUNT_ID}"
)

for BUCKET in "${BUCKETS[@]}"; do
  echo "Creating bucket: $BUCKET"

  # us-east-1 does NOT use --create-bucket-configuration
  aws s3api create-bucket \
    --bucket "$BUCKET" \
    --region "$REGION"

  aws s3api put-bucket-versioning \
    --bucket "$BUCKET" \
    --versioning-configuration Status=Enabled

  aws s3api put-bucket-tagging \
    --bucket "$BUCKET" \
    --tagging '{
      "TagSet": [
        {"Key": "Project", "Value": "ESG"},
        {"Key": "Env", "Value": "POC"},
        {"Key": "Team", "Value": "Sustainability"}
      ]
    }'

  aws s3api put-public-access-block \
    --bucket "$BUCKET" \
    --public-access-block-configuration \
      BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

  # Lifecycle: keep only 1 noncurrent version, delete older ones
  aws s3api put-bucket-lifecycle-configuration \
    --bucket "$BUCKET" \
    --lifecycle-configuration '{
      "Rules": [
        {
          "ID": "DeleteOldNoncurrentVersions",
          "Status": "Enabled",
          "Filter": {},
          "NoncurrentVersionExpiration": {
            "NewerNoncurrentVersions": 1,
            "NoncurrentDays": 1
          }
        }
      ]
    }'

  echo "  ✅ $BUCKET created"
done

# =============================================================================
# 3. CREATE FOLDER STRUCTURE
# =============================================================================

DATA_DOMAINS=("emissions" "energy" "water" "waste" "social" "governance")
REPORTING_YEARS=("2023" "2024")

for BUCKET in "${BUCKETS[@]}"; do
  for YEAR in "${REPORTING_YEARS[@]}"; do
    for DOMAIN in "${DATA_DOMAINS[@]}"; do
      aws s3api put-object \
        --bucket "$BUCKET" \
        --key "${YEAR}/${DOMAIN}/" \
        --content-length 0
    done
  done
  echo "  ✅ Folder structure created in $BUCKET"
done

echo ""
echo "========================================="
echo "  D1 SETUP COMPLETE!"
echo "========================================="
