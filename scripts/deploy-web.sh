#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

: "${ICO_STACK_NAME:=IcoStack-demo}"

caller_arn="$(aws sts get-caller-identity --query Arn --output text)"
if [[ "$caller_arn" == *":root" ]]; then
  echo "Refusing to deploy from an AWS root session. Use the approved GitHub OIDC role or IAM Identity Center." >&2
  exit 1
fi

output() {
  aws cloudformation describe-stacks \
    --stack-name "$ICO_STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue | [0]" \
    --output text
}

marketing_bucket="$(output MarketingBucketName)"
responder_bucket="$(output ResponderBucketName)"
distribution_id="$(output DistributionId)"
api_url="$(output ApiUrl)"
web_client_id="$(output WebUserPoolClientId)"
cognito_url="$(output CognitoManagedLoginUrl)"

for value in "$marketing_bucket" "$responder_bucket" "$distribution_id" "$api_url" "$web_client_id" "$cognito_url"; do
  if [[ -z "$value" || "$value" == "None" ]]; then
    echo "The deployed stack is missing a required web output." >&2
    exit 1
  fi
done

npm run build -w @incaseof/marketing
npm run build -w @incaseof/responder

runtime_dir="$(mktemp -d)"
trap 'rm -rf "$runtime_dir"' EXIT
jq -n \
  --arg apiUrl "${ICO_PUBLIC_API_URL:-$api_url}" \
  --arg cognitoDomain "$cognito_url" \
  --arg webClientId "$web_client_id" \
  '{apiUrl: $apiUrl, cognitoDomain: $cognitoDomain, webClientId: $webClientId}' \
  > "$runtime_dir/runtime-config.json"

aws s3 sync apps/marketing/out "s3://$marketing_bucket" --only-show-errors
aws s3 cp "$runtime_dir/runtime-config.json" "s3://$marketing_bucket/runtime-config.json" \
  --cache-control 'no-store' --content-type 'application/json' --only-show-errors
aws s3 sync apps/responder/out "s3://$responder_bucket" --only-show-errors
aws cloudfront create-invalidation --distribution-id "$distribution_id" --paths '/*' >/dev/null

echo "Static clients published through CloudFront."
