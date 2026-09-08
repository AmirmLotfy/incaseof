#!/usr/bin/env bash
set -euo pipefail

# Repeatable live acceptance for the deterministic half of the public judge demo.
# This intentionally starts after compilation: Bedrock/AgentCore has its own canary gate.
# The API issues a synthetic, 30-minute tenant and the demo worker redirects all delivery
# to SAFE_SINK. No token is printed or written to disk.

: "${ICO_DEMO_API_URL:?Set ICO_DEMO_API_URL to the deployed demo API origin}"
if [[ "${ICO_ACCEPT_SYNTHETIC_MUTATION:-}" != "1" ]]; then
  echo "Refusing to create a synthetic Drill without ICO_ACCEPT_SYNTHETIC_MUTATION=1." >&2
  exit 2
fi
if [[ "$ICO_DEMO_API_URL" != https://* ]]; then
  echo "ICO_DEMO_API_URL must be HTTPS." >&2
  exit 2
fi

api="${ICO_DEMO_API_URL%/}"
max_polls="${ICO_DEMO_MAX_POLLS:-30}"
poll_seconds="${ICO_DEMO_POLL_SECONDS:-2}"

request() {
  local raw
  raw=$(curl --silent --show-error --max-time 20 --write-out $'\n%{http_code}' "$@")
  RESPONSE_CODE="${raw##*$'\n'}"
  RESPONSE_BODY="${raw%$'\n'*}"
}

expect_code() {
  local expected="$1"
  local label="$2"
  if [[ "$RESPONSE_CODE" != "$expected" ]]; then
    printf '%s failed with HTTP %s: %s\n' "$label" "$RESPONSE_CODE" \
      "$(printf '%s' "$RESPONSE_BODY" | jq -c 'del(.token,.sessionToken,.signedToken,.responderUrl)' 2>/dev/null || printf '<non-json>')" >&2
    exit 1
  fi
}

request --request POST "$api/v1/demo/session"
expect_code 201 "demo session"
session_token=$(printf '%s' "$RESPONSE_BODY" | jq -er '.sessionToken')

plan_payload=$(jq -nc '{
  type:"ROUTINE",
  label:"Mona live acceptance drill",
  timezone:"UTC",
  trigger:{kind:"RECURRING",timeOfDay:"21:00"},
  grace:{seconds:600},
  steps:[
    {sequence:1,offsetSeconds:0,action:"PUSH_SUBJECT"},
    {sequence:2,offsetSeconds:600,action:"PUSH_SUBJECT"},
    {sequence:3,offsetSeconds:1200,action:"SMS_SUBJECT"},
    {sequence:4,offsetSeconds:1500,action:"MESSAGE_RESPONDER",targetRole:"PRIMARY"},
    {sequence:5,offsetSeconds:2700,action:"MESSAGE_RESPONDER",targetRole:"BACKUP"}
  ],
  stopConditions:["SUBJECT_EXPLICIT_CONFIRMATION","RESPONDER_VERIFIED_CONTACT"],
  contextPolicy:{location:"NEVER",battery:"AFTER_SUBJECT_CALL_FAILED"},
  leaseSeconds:600
}')

request --request POST "$api/v1/demo/plans" \
  --header "Authorization: Bearer $session_token" \
  --header 'Content-Type: application/json' \
  --data "$plan_payload"
expect_code 201 "create plan"
plan_id=$(printf '%s' "$RESPONSE_BODY" | jq -er '.planId')

idempotency_key="live-acceptance-$(date -u +%Y%m%dT%H%M%SZ)-$$"
request --request POST "$api/v1/demo/plans/$plan_id/test" \
  --header "Authorization: Bearer $session_token" \
  --header "Idempotency-Key: $idempotency_key"
expect_code 202 "start Drill"
moment_id=$(printf '%s' "$RESPONSE_BODY" | jq -er '.moment.momentId')
time_scale=$(printf '%s' "$RESPONSE_BODY" | jq -er '.moment.timeScale')

alert_id=""
for ((poll = 1; poll <= max_polls; poll++)); do
  request "$api/v1/demo/moments/next" --header "Authorization: Bearer $session_token"
  expect_code 200 "poll Moment"
  alert_id=$(printf '%s' "$RESPONSE_BODY" | jq -r '.alertId // empty')
  [[ -n "$alert_id" ]] && break
  sleep "$poll_seconds"
done
if [[ -z "$alert_id" ]]; then
  echo "No Alert materialized before the polling deadline." >&2
  exit 1
fi

request "$api/v1/demo/alerts/$alert_id/responder-link" \
  --header "Authorization: Bearer $session_token"
expect_code 200 "mint responder link"
responder_url=$(printf '%s' "$RESPONSE_BODY" | jq -er '.responderUrl')
responder_token="${responder_url##*/}"

claim_body=""
for ((poll = 1; poll <= max_polls; poll++)); do
  request --request POST "$api/v1/r/$responder_token/claim"
  if [[ "$RESPONSE_CODE" == "200" ]]; then
    claim_body="$RESPONSE_BODY"
    break
  fi
  # Before the Circle rung is current, the same role-scoped token is deliberately denied.
  if [[ "$RESPONSE_CODE" != "422" ]]; then
    expect_code 200 "claim Alert"
  fi
  sleep "$poll_seconds"
done
if [[ -z "$claim_body" ]] || [[ "$(printf '%s' "$claim_body" | jq -r '.state')" != "CHECKING" ]]; then
  echo "The responder never acquired a checking lease." >&2
  exit 1
fi

request --request POST "$api/v1/r/$responder_token/resolve"
expect_code 200 "resolve Alert"
resolve_body="$RESPONSE_BODY"
if [[ "$(printf '%s' "$resolve_body" | jq -r '.state')" != "RESOLVED" ]]; then
  echo "Explicit responder resolution did not produce RESOLVED." >&2
  exit 1
fi

request "$api/v1/demo/alerts/$alert_id/timeline" \
  --header "Authorization: Bearer $session_token"
expect_code 200 "read audit timeline"
timeline_body="$RESPONSE_BODY"

for required in MOMENT_DUE STATE_CIRCLE_ESCALATION ALERT_CLAIMED RESPONDER_VERIFIED; do
  if ! printf '%s' "$timeline_body" | jq -e --arg event "$required" \
    'any(.events[]; .event == $event)' >/dev/null; then
    echo "Audit timeline is missing $required." >&2
    exit 1
  fi
done
if ! printf '%s' "$timeline_body" | jq -e \
  '[.events[].metadata.providerReference? | select(.)] | length > 0 and all(.[]; startswith("safe-sink:"))' >/dev/null; then
  echo "Demo delivery was not confined to auditable safe-sink references." >&2
  exit 1
fi

printf '%s' "$timeline_body" | jq \
  --arg verifiedAt "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg planId "$plan_id" \
  --arg momentId "$moment_id" \
  --arg alertId "$alert_id" \
  --argjson timeScale "$time_scale" \
  '{
    verifiedAt:$verifiedAt,
    syntheticTenant:true,
    timeScale:$timeScale,
    planId:$planId,
    momentId:$momentId,
    alertId:$alertId,
    terminalState:"RESOLVED",
    eventCount:(.events|length),
    events:[.events[].event],
    safeSinkReferences:([.events[].metadata.providerReference? | select(.)] | unique),
    tokensRedacted:true
  }'
