#!/usr/bin/env bash
# Updates the EXISTING pipeline Lambdas (section_gen, validation, athena_query, assembly_doc) with the new code, bundles the
# shared modules flat at the zip root (the handlers import them as top-level modules), merges the new environment variables,
# and syncs templates (prompts/templates/) and prompts (prompts/) to the KB bucket, and uploads the Scope 3 operational data.
#
#   AWS_REGION=us-east-1 ACCOUNT_ID=061039769766 USAGE_TABLE=esg-llm-usage PII_TOKEN_SECRET_ARN=<PiiSecretArn> bash scripts/package_lambdas.sh
#   DRY_RUN=1 ... only builds the zips under build/lambda-zips and prints what it would do.
set -euo pipefail
cd "$(dirname "$0")/.."
REGION="${AWS_REGION:-us-east-1}"
if [ -n "${DRY_RUN:-}" ]; then ACCOUNT_ID="${ACCOUNT_ID:-061039769766}"; else ACCOUNT_ID="${ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"; fi
USAGE_TABLE="${USAGE_TABLE:-esg-llm-usage}"
PROFILE_ROUTING="${MODEL_ROUTING_PROFILE:-quality}"
OUT=build/lambda-zips
mkdir -p "$OUT"

declare -A FN=( [section_gen]=esg-section-gen [validation]=esg-validation [athena_query]=esg-athena-query [assembly_doc]=esg-assembly-doc )

for dir in "${!FN[@]}"; do
  name="${FN[$dir]}"
  stage=$(mktemp -d)
  cp "lambda/$dir/handler.py" "$stage/"
  cp lambda/_shared/*.py "$stage/"
  (cd "$stage" && python3 -c "import zipfile,os,sys; z=zipfile.ZipFile(sys.argv[1],'w',zipfile.ZIP_DEFLATED); [z.write(f) for f in sorted(os.listdir('.')) if f.endswith('.py')]; z.close()" "$OLDPWD/$OUT/$dir.zip")
  rm -rf "$stage"
  echo "built $OUT/$dir.zip -> $name"
  [ -n "${DRY_RUN:-}" ] && continue
  aws lambda update-function-code --region "$REGION" --function-name "$name" --zip-file "fileb://$OUT/$dir.zip" --output text --query LastModified
  aws lambda wait function-updated --region "$REGION" --function-name "$name"
done

if [ -z "${DRY_RUN:-}" ]; then
  # merge (never replace) environment variables
  merge_env() { # function-name KEY=VALUE...
    local fn="$1"; shift
    local current; current=$(aws lambda get-function-configuration --region "$REGION" --function-name "$fn" --query 'Environment.Variables' --output json)
    local merged; merged=$(python3 - "$current" "$@" <<'PY'
import json, sys
cur = json.loads(sys.argv[1]) or {}
for kv in sys.argv[2:]:
    k, v = kv.split("=", 1); cur[k] = v
print(json.dumps({"Variables": cur}))
PY
)
    aws lambda update-function-configuration --region "$REGION" --function-name "$fn" --environment "$merged" --output text --query LastModified
    aws lambda wait function-updated --region "$REGION" --function-name "$fn"
  }
  merge_env esg-section-gen "USAGE_TABLE=$USAGE_TABLE" "MODEL_ROUTING_PROFILE=$PROFILE_ROUTING" "USAGE_TTL_DAYS=14" \
    "PII_TOKEN_SECRET_ARN=${PII_TOKEN_SECRET_ARN:?set PII_TOKEN_SECRET_ARN (CDK output PiiSecretArn)}" "PII_REQUIRE_SECRET=1"
  merge_env esg-validation "VALIDATOR_CALIBRATION=on"

  aws s3 sync templates "s3://esg-kb-documents-$ACCOUNT_ID/prompts/templates/" --region "$REGION" --exclude "*" --include "*.txt"
  aws s3 sync prompts "s3://esg-kb-documents-$ACCOUNT_ID/prompts/" --region "$REGION" --exclude "*" --include "*.txt"
  aws s3 sync data/synthetic/scope3_operational "s3://esg-data-raw-$ACCOUNT_ID/raw/scope3_operational_activity/" --region "$REGION" --exclude "*.csv"
fi
echo "done"
