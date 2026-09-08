#!/usr/bin/env bash
# Stage the Lambda deployment asset.
#
# CDK points at infra/cdk/assets/lambda. This copies the services package into it and
# installs the runtime dependencies for Lambda's platform, not for this laptop --
# a wheel built for macOS arm64 fails at import time on Lambda, and it fails there, not here.
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1

TARGET="infra/cdk/assets/lambda"
PYTHON_VERSION="3.12"
# uv's triple format, not pip's. manylinux2014 is glibc 2.17, comfortably below the
# Lambda runtime's, so wheels built for it load there.
PLATFORM="x86_64-manylinux2014"

echo "staging $TARGET"
rm -rf "$TARGET"
mkdir -p "$TARGET"

# Rewrite the placeholder rather than trying to preserve it across the rm above. It is
# tracked in git so that `cdk synth` resolves the asset path on a fresh clone, before
# anything has been built — without it, CI fails every template assertion at once with an
# error that points at the constructs rather than at the missing directory.
cat > "$TARGET/.gitkeep" <<'KEEP'
Populated by scripts/build-lambda.sh. Tracked so `cdk synth` resolves the asset path on a
fresh clone. Everything else in this directory is generated and gitignored.
KEEP

# Application code. Tests and caches are not deployment artefacts.
rsync -a --quiet \
  --exclude '__pycache__' --exclude 'tests' --exclude '*.pyc' \
  services "$TARGET/"

# The JSON Schema is loaded at import time by services/domain/compiler.py, so it is code
# as far as the package is concerned. Omitting it does not fail the build — it fails at
# cold start, inside whichever Lambda first imports the compiler.
rsync -a --quiet packages/domain-schemas "$TARGET/packages/"

# Runtime dependencies, listed explicitly rather than exported from pyproject.
#
# The project depends on the whole agent stack — Strands, AgentCore Runtime and their
# transitive tree — none of which these handlers import. Exporting everything would ship tens of
# megabytes of unused code to every function, slow every cold start, and drag in packages
# with no wheel for Lambda's platform.
#
# boto3 and botocore are pinned because the API facade invokes AgentCore Runtime, whose
# client is not guaranteed to exist in Lambda's preinstalled SDK version. Shipping the pair
# together avoids a boto3/botocore version skew at cold start.
#
# The agent Lambda in Phase 5 needs a different set, and gets its own asset.
cat > "$TARGET/requirements.txt" <<'REQ'
jsonschema==4.26.0
boto3==1.43.78
botocore==1.43.78
REQ

uv pip install \
  --target "$TARGET" \
  --requirement "$TARGET/requirements.txt" \
  --python-platform "$PLATFORM" \
  --python-version "$PYTHON_VERSION" \
  --only-binary :all: \
  --quiet

# Fail loudly here rather than at cold start in production.
for required in \
  services/domain/compiler.py \
  services/handlers/agent_tool_target.py \
  services/adapters/agentcore.py \
  packages/domain-schemas/compiled-plan.schema.json \
  boto3/__init__.py \
  botocore/__init__.py; do
  if [ ! -f "$TARGET/$required" ]; then
    echo "ERROR: $required is missing from the package" >&2
    exit 1
  fi
done

native_validator="$(find "$TARGET" -name 'rpds*.so' -print -quit)"
if [ -n "$native_validator" ]; then
  file "$native_validator" | grep -q "ELF 64-bit.*x86-64"
fi

printf 'staged %s (%s)\n' "$TARGET" "$(du -sh "$TARGET" | cut -f1)"
