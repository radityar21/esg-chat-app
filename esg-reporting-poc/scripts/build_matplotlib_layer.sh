#!/bin/bash
# =============================================================================
# Build matplotlib Lambda Layer for ESG AssemblyDoc
# Run this in AWS CloudShell (us-east-1)
# =============================================================================

set -e

echo "=== Building matplotlib Lambda Layer ==="

# Clean up any previous build
rm -rf /tmp/lambda-layer /tmp/matplotlib-layer.zip

# Create layer directory structure
mkdir -p /tmp/lambda-layer/python

# Install matplotlib + dependencies for Lambda (x86_64, Python 3.11)
pip install matplotlib numpy pillow \
  --target /tmp/lambda-layer/python \
  --platform manylinux2014_x86_64 \
  --only-binary=:all: \
  --python-version 3.11 \
  --no-deps 2>/dev/null || \
pip install matplotlib numpy pillow \
  --target /tmp/lambda-layer/python

# Remove unnecessary files to reduce size
echo "=== Cleaning up unnecessary files ==="
find /tmp/lambda-layer/python -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true
find /tmp/lambda-layer/python -name "*.pyc" -delete 2>/dev/null || true
find /tmp/lambda-layer/python -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
rm -rf /tmp/lambda-layer/python/matplotlib/mpl-data/sample_data 2>/dev/null || true
rm -rf /tmp/lambda-layer/python/matplotlib/mpl-data/fonts/afm 2>/dev/null || true
rm -rf /tmp/lambda-layer/python/matplotlib/mpl-data/fonts/pdfcorefonts 2>/dev/null || true
rm -rf /tmp/lambda-layer/python/numpy/tests 2>/dev/null || true
rm -rf /tmp/lambda-layer/python/PIL/tests 2>/dev/null || true

# Check size
echo "=== Layer size ==="
du -sh /tmp/lambda-layer/python/

# Package as zip
cd /tmp/lambda-layer
zip -r /tmp/matplotlib-layer.zip python/ -x "*.pyc" "__pycache__/*"
echo "=== ZIP size ==="
ls -lh /tmp/matplotlib-layer.zip

# Upload to S3 (temporary storage)
echo "=== Uploading to S3 ==="
aws s3 cp /tmp/matplotlib-layer.zip s3://esg-data-raw-061039769766/layers/matplotlib-layer.zip --region us-east-1

# Publish Lambda Layer
echo "=== Publishing Lambda Layer ==="
LAYER_ARN=$(aws lambda publish-layer-version \
  --layer-name esg-matplotlib-layer \
  --description "Matplotlib + NumPy + Pillow for ESG chart generation" \
  --content S3Bucket=esg-data-raw-061039769766,S3Key=layers/matplotlib-layer.zip \
  --compatible-runtimes python3.11 python3.12 \
  --region us-east-1 \
  --query 'LayerVersionArn' \
  --output text)

echo "=== Layer published: $LAYER_ARN ==="

# Get existing python-docx layer ARN
DOCX_LAYER=$(aws lambda get-function-configuration \
  --function-name esg-assembly-doc \
  --region us-east-1 \
  --query 'Layers[0].Arn' \
  --output text)

echo "=== Existing python-docx layer: $DOCX_LAYER ==="

# Attach BOTH layers to AssemblyDoc Lambda + increase memory + timeout
echo "=== Updating esg-assembly-doc configuration ==="
aws lambda update-function-configuration \
  --function-name esg-assembly-doc \
  --layers "$DOCX_LAYER" "$LAYER_ARN" \
  --timeout 300 \
  --memory-size 2048 \
  --region us-east-1

echo ""
echo "=== DONE ==="
echo "Layer ARN: $LAYER_ARN"
echo "AssemblyDoc updated: 2048MB memory, 300s timeout, matplotlib layer attached"
echo ""
echo "Next: deploy updated handler.py code for esg-assembly-doc"
