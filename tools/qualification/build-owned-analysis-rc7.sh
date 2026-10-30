#!/bin/sh
# Build a separate source-derived runtime; never patch an installed package.
set -eu
if [ "$#" -ne 2 ]; then
    echo "usage: $0 NEW_OUTPUT_DIRECTORY PINNED_DEPENDENCY_CONSTRAINTS" >&2
    exit 2
fi
output=$1
constraints=$2
test -f "$constraints"
mkdir "$output"  # Refuse reuse, including a retained failed build.
output=$(cd "$output" && pwd)
constraints=$(cd "$(dirname "$constraints")" && pwd)/$(basename "$constraints")
recipe=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
archive="$output/source.tar.gz"
curl --fail --location --silent --show-error \
    'https://files.pythonhosted.org/packages/ca/19/15940c93bebf10662cce19aa13c925f187bba360414dc1ac5fe3092a6e05/spec_kitty_cli-4.0.0rc7.tar.gz' \
    --output "$archive"
printf '%s  %s\n' '91e98774b7a69a273f9146656482e1e2bddd274a2178dfc6ac9c1f3bcede0c80' "$archive" | shasum -a 256 --check
mkdir "$output/source"
tar -xzf "$archive" -C "$output/source" --strip-components=1
patch --batch --fuzz=0 -p1 -d "$output/source" < "$recipe/owned-analysis-rc7.patch"
# This local identity explicitly distinguishes the result from published RC7.
sed 's/^version = "4.0.0rc7"$/version = "4.0.0rc7+crucible.ownedanalysis.2"/' \
    "$output/source/pyproject.toml" > "$output/source/pyproject.toml.local"
grep -q '^version = "4.0.0rc7+crucible.ownedanalysis.2"$' "$output/source/pyproject.toml.local"
mv "$output/source/pyproject.toml.local" "$output/source/pyproject.toml"
uv venv "$output/venv"
uv pip install --python "$output/venv/bin/python" --constraint "$constraints" "$output/source"
uv pip freeze --python "$output/venv/bin/python" > "$output/installed-requirements.log"
shasum -a 256 "$archive" "$recipe/owned-analysis-rc7.patch" "$constraints" "$output/source/pyproject.toml" > "$output/build-inputs.sha256.log"
"$output/venv/bin/spec-kitty" --version > "$output/version.log"
cat "$output/version.log"
echo "Retain this output and receipts until consumer replay and owner closeout."
