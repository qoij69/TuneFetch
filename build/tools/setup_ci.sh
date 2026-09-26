#!/usr/bin/env bash
# build/tools/setup_ci.sh - wires up the GitHub Actions build
# (lunch tunefetch-allproducts-eng && make tunefetch)
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

mkdir -p .github/workflows
if [ -f "build/ci/build.yml" ]; then
    cp build/ci/build.yml .github/workflows/build.yml
    echo "Copied build/ci/build.yml into .github/workflows/build.yml"
else
    echo "Could not find build/ci/build.yml - is your tree intact?"
    exit 1
fi

echo
echo "Next steps:"
echo "  1. Commit and push this tree to a GitHub repository"
echo "     (including the new .github/workflows/build.yml file)."
echo "  2. Open the 'Actions' tab on GitHub - a build will run"
echo "     automatically and produce tunefetch_linux, tunefetch_windows"
echo "     and tunefetch_macos artifacts, downloadable from that run."
