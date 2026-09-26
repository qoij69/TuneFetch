#!/usr/bin/env bash
# ============================================================
#  TuneFetch build environment
#  Usage:  source build/envsetup.sh
# ============================================================
# Only meant to be sourced, never executed directly - it needs to
# export variables and define functions (lunch, m, mka, croot)
# into your *current* shell.

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    echo "This script must be sourced, not run:"
    echo "    source build/envsetup.sh"
    exit 1
fi

export TUNEFETCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

case "$(uname -s)" in
    Darwin*) export TUNEFETCH_HOST_OS="macos" ;;
    Linux*)  export TUNEFETCH_HOST_OS="linux" ;;
    *)       export TUNEFETCH_HOST_OS="linux" ;;
esac

lunch() {
    local choice combo host_cap
    host_cap="$(echo "${TUNEFETCH_HOST_OS:0:1}" | tr a-z A-Z)${TUNEFETCH_HOST_OS:1}"

    if [ -n "$1" ]; then
        combo="$1"
    else
        echo
        echo "You're building on $host_cap."
        echo
        echo "Lunch menu... pick a combo:"
        echo "     1. tunefetch-linux-userdebug"
        echo "     2. tunefetch-windows-userdebug     (cross-build: prints instructions on this host)"
        echo "     3. tunefetch-macos-userdebug       (cross-build: prints instructions on this host)"
        echo "     4. tunefetch-allproducts-eng       (sets up the GitHub Actions build for all three)"
        echo
        read -rp "Which would you like? [tunefetch-${TUNEFETCH_HOST_OS}-userdebug] " choice
        case "${choice:-1}" in
            1) combo="tunefetch-linux-userdebug" ;;
            2) combo="tunefetch-windows-userdebug" ;;
            3) combo="tunefetch-macos-userdebug" ;;
            4) combo="tunefetch-allproducts-eng" ;;
            *) combo="$choice" ;;
        esac
    fi

    case "$combo" in
        tunefetch-linux-userdebug)      export TUNEFETCH_PRODUCT="linux";       export TUNEFETCH_VARIANT="userdebug" ;;
        tunefetch-windows-userdebug)    export TUNEFETCH_PRODUCT="windows";     export TUNEFETCH_VARIANT="userdebug" ;;
        tunefetch-macos-userdebug)      export TUNEFETCH_PRODUCT="macos";       export TUNEFETCH_VARIANT="userdebug" ;;
        tunefetch-allproducts-eng)      export TUNEFETCH_PRODUCT="allproducts"; export TUNEFETCH_VARIANT="eng" ;;
        *)
            echo "Invalid combo: $combo"
            echo "Try one of: tunefetch-linux-userdebug, tunefetch-windows-userdebug,"
            echo "            tunefetch-macos-userdebug, tunefetch-allproducts-eng"
            return 1
            ;;
    esac
    export TUNEFETCH_OUT="$TUNEFETCH_ROOT/out/target/product/$TUNEFETCH_PRODUCT"

    echo
    echo "============================================"
    echo "PLATFORM_VERSION_CODENAME=REL"
    echo "PLATFORM_VERSION=1.1"
    echo "TARGET_PRODUCT=tunefetch_${TUNEFETCH_PRODUCT}"
    echo "TARGET_BUILD_VARIANT=${TUNEFETCH_VARIANT}"
    echo "HOST_OS=${TUNEFETCH_HOST_OS}"
    echo "OUT_DIR=out/target/product/${TUNEFETCH_PRODUCT}"
    echo "============================================"
    echo
}

croot() { cd "$TUNEFETCH_ROOT" || return 1; }

m() { (croot && make "$@"); }
mka() { m "$@"; }
mm() { m tunefetch; }

echo "============================================"
echo " TuneFetch build environment ready."
echo " Run 'lunch' to choose a target, then 'make tunefetch'"
echo " (or just 'm', 'mka', 'mm')."
echo "============================================"
