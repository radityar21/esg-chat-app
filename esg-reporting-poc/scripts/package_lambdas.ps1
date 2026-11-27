<#
 Updates the EXISTING pipeline Lambdas (section_gen, validation, athena_query, assembly_doc) with the new code,
 bundles the shared modules flat at the zip root, MERGES the new environment variables (never replaces them),
 and syncs templates, prompts and the Scope 3 seed data.

 Run from esg-reporting-poc\ :
   .\scripts\package_lambdas.ps1 -PiiSecretArn <PiiSecretArn output of EsgPlatformStack>
   .\scripts\package_lambdas.ps1 -PiiSecretArn x -DryRun      # only builds the zips under build\lambda-zips
#>
param(
  [Parameter(Mandatory = $true)][string]$PiiSecretArn,
  [string]$Region = "us-east-1",
  [string]$AccountId = "061039769766",
  [string]$UsageTable = "esg-llm-usage",
  [string]$RoutingProfile = "quality",
  [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$out = Join-Path $root "build\lambda-zips"
New-Item -ItemType Directory -Force $out | Out-Null

$fns = [ordered]@{ section_gen = "esg-section-gen"; validation = "esg-validation"; athena_query = "esg-athena-query"; assembly_doc = "esg-assembly-doc" }

foreach ($dir in $fns.Keys) {
  $name = $fns[$dir]
  $stage = Join-Path ([System.IO.Path]::GetTempPath()) ("esgpkg_" + [guid]::NewGuid().ToString("N"))
  New-Item -ItemType Directory $stage | Out-Null
  Copy-Item "lambda\$dir\handler.py" $stage
  Get-ChildItem "lambda\_shared\*.py" | Copy-Item -Destination $stage
  $zip = Join-Path $out "$dir.zip"
  if (Test-Path $zip) { Remove-Item $zip }
  Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zip
  Remove-Item $stage -Recurse -Force
  Write-Host "built $zip -> $name"
  if ($DryRun) { continue }
  aws lambda update-function-code --region $Region --function-name $name --zip-file "fileb://$zip" --query LastModified --output text
  aws lambda wait function-updated --region $Region --function-name $name
}
if ($DryRun) { Write-Host "dry run done"; return }

function Merge-LambdaEnv([string]$fn, [hashtable]$add) {
  $json = aws lambda get-function-configuration --region $Region --function-name $fn --query "Environment.Variables" --output json
  $vars = @{}
  if ($json -and $json -ne "null") { ($json | ConvertFrom-Json).PSObject.Properties | ForEach-Object { $vars[$_.Name] = [string]$_.Value } }
  foreach ($k in $add.Keys) { $vars[$k] = $add[$k] }
  $file = Join-Path ([System.IO.Path]::GetTempPath()) "env_$fn.json"
  (@{ Variables = $vars } | ConvertTo-Json -Depth 5) | Set-Content $file -Encoding ascii
  aws lambda update-function-configuration --region $Region --function-name $fn --environment "file://$file" --query LastModified --output text
  aws lambda wait function-updated --region $Region --function-name $fn
}
Merge-LambdaEnv "esg-section-gen" @{ USAGE_TABLE = $UsageTable; MODEL_ROUTING_PROFILE = $RoutingProfile; USAGE_TTL_DAYS = "14"; PII_TOKEN_SECRET_ARN = $PiiSecretArn; PII_REQUIRE_SECRET = "1" }
Merge-LambdaEnv "esg-validation" @{ VALIDATOR_CALIBRATION = "on" }

aws s3 sync templates "s3://esg-kb-documents-$AccountId/prompts/templates/" --region $Region --exclude "*" --include "*.txt"
aws s3 sync prompts "s3://esg-kb-documents-$AccountId/prompts/" --region $Region --exclude "*" --include "*.txt"
Write-Host "done"
