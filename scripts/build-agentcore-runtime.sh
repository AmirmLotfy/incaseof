#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
runtime_source="$repo_root/agentcore/runtime"
asset_dir="$repo_root/infra/cdk/assets/agentcore"

mkdir -p "$asset_dir"
find "$asset_dir" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +

uv pip install \
  --quiet \
  --python-version 3.12 \
  --python-platform aarch64-manylinux_2_28 \
  --target "$asset_dir" \
  --requirements "$runtime_source/requirements.txt"

cp "$runtime_source/main.py" "$asset_dir/main.py"
mkdir -p "$asset_dir/services" "$asset_dir/packages/domain-schemas"
cp "$repo_root/services/__init__.py" "$asset_dir/services/__init__.py"
cp -R "$repo_root/services/agent" "$asset_dir/services/agent"
cp -R "$repo_root/services/domain" "$asset_dir/services/domain"
cp "$repo_root/packages/domain-schemas/compiled-plan.schema.json" \
  "$asset_dir/packages/domain-schemas/compiled-plan.schema.json"

test -f "$asset_dir/main.py"
test -f "$asset_dir/bedrock_agentcore/__init__.py"
test -f "$asset_dir/strands/__init__.py"
native_core="$(find "$asset_dir/pydantic_core" -name '_pydantic_core*.so' -print -quit)"
test -n "$native_core"
file "$native_core" | grep -q "ELF 64-bit.*ARM aarch64"

smoke_image="public.ecr.aws/docker/library/python:3.12-slim"
if command -v docker >/dev/null 2>&1 \
  && docker info >/dev/null 2>&1 \
  && docker image inspect "$smoke_image" >/dev/null 2>&1; then
  docker run --rm --platform linux/arm64 \
    -v "$asset_dir:/asset:ro" \
    -w /asset \
    -e AWS_REGION=us-east-1 \
    "$smoke_image" \
    python -c "import main; assert main.app.handlers.get('main') is main.invoke"
else
  echo "agentcore artifact structure and ARM64 ABI verified; container import smoke skipped" >&2
fi

find "$asset_dir" -type f -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256 \
  > "$asset_dir.sha256"
echo "agentcore artifact: $asset_dir"
