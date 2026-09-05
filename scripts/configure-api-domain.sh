#!/usr/bin/env bash
set -euo pipefail

# Keep the existing canonical API custom domain pointed at the current demo stack.
# The domain predates the stack and has one externally managed empty-path mapping.
# Update that mapping in place; never delete or guess among multiple mappings.

stack_name="${ICO_STACK_NAME:-IcoStack-demo}"
domain_name="${ICO_API_DOMAIN:-api.incaof.com}"

api_url=$(aws cloudformation describe-stacks \
  --stack-name "$stack_name" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue | [0]" \
  --output text \
  --no-cli-pager)

if [[ "$api_url" != https://*.execute-api.*.amazonaws.com ]]; then
  echo "Refusing unexpected ApiUrl for $stack_name: $api_url" >&2
  exit 1
fi
api_host="${api_url#https://}"
api_id="${api_host%%.*}"

mapping_ids=$(aws apigatewayv2 get-api-mappings \
  --domain-name "$domain_name" \
  --query "Items[?ApiMappingKey==''].ApiMappingId" \
  --output text \
  --no-cli-pager)
read -r -a mapping_id_list <<< "$mapping_ids"
if [[ ${#mapping_id_list[@]} -ne 1 || -z "${mapping_id_list[0]}" || "${mapping_id_list[0]}" == "None" ]]; then
  echo "Expected exactly one empty-path mapping for $domain_name." >&2
  exit 1
fi
mapping_id="${mapping_id_list[0]}"

current_api_id=$(aws apigatewayv2 get-api-mapping \
  --domain-name "$domain_name" \
  --api-mapping-id "$mapping_id" \
  --query ApiId \
  --output text \
  --no-cli-pager)

if [[ "$current_api_id" != "$api_id" ]]; then
  aws apigatewayv2 update-api-mapping \
    --domain-name "$domain_name" \
    --api-mapping-id "$mapping_id" \
    --api-id "$api_id" \
    --stage '$default' \
    --no-cli-pager >/dev/null
fi

verified_api_id=$(aws apigatewayv2 get-api-mapping \
  --domain-name "$domain_name" \
  --api-mapping-id "$mapping_id" \
  --query ApiId \
  --output text \
  --no-cli-pager)
if [[ "$verified_api_id" != "$api_id" ]]; then
  echo "Canonical mapping verification failed: expected $api_id, found $verified_api_id." >&2
  exit 1
fi

descriptor=$(curl --fail-with-body --silent --show-error --max-time 20 "https://$domain_name/")
python3 -c \
  'import json,sys; value=json.load(sys.stdin); assert value == {"service":"In Case Of API","status":"ok","productBoundary":"Monitors expected moments, not people."}' \
  <<< "$descriptor"

printf 'canonical API: https://%s -> %s (%s)\n' "$domain_name" "$api_id" "$mapping_id"
