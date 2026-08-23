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

# Runtime dependencies, listed explicitly rather than exported from pyproject.
#
# The project depends on the whole agent stack — strands, google-genai and their transitive
# tree — none of which these handlers import. Exporting everything would ship tens of
# megabytes of unused code to every function, slow every cold start, and drag in packages
# with no wheel for Lambda's platform.
#
# boto3 and botocore are omitted deliberately: the runtime already provides them, and using
# AWS's build avoids a version skew between the SDK and the environment it runs in.
#
# The agent Lambda in Phase 5 needs a different set, and gets its own asset.
cat > "$TARGET/requirements.txt" <<'REQ'
jsonschema==4.26.0
REQ

uv pip install \
  --target "$TARGET" \
  --requirement "$TARGET/requirements.txt" \
  --python-platform "$PLATFORM" \
  --python-version "$PYTHON_VERSION" \
  --only-binary :all: \
  --quiet

printf 'staged %s (%s)\n' "$TARGET" "$(du -sh "$TARGET" | cut -f1)"
