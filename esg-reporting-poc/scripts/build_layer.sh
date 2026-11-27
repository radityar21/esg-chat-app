#!/usr/bin/env bash
# Builds build/layer/python with a recent boto3 (the Lambda runtime's bundled boto3 may predate the bedrock-agentcore client).
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf build/layer && mkdir -p build/layer/python
python3 -m pip install --quiet --upgrade --target build/layer/python "boto3>=1.40" 
echo "layer ready: $(du -sh build/layer | cut -f1)"
