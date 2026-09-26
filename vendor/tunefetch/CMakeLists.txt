# ============================================================
#  vendor/tunefetch/CMakeLists.txt
# ============================================================
# This is a module manifest, not a build entry point - the real
# build is driven by build/envsetup.sh + the top-level Makefile
# (PyInstaller under the hood, not CMake/make in the compiler
# sense). This file just documents tunefetch's dependency graph
# in the same shape the rest of the tree uses.
#
#   source build/envsetup.sh
#   lunch
#   make tunefetch

cmake_minimum_required(VERSION 3.20)
project(TuneFetch VERSION 1.1 LANGUAGES NONE)

set(TUNEFETCH_SOURCE tunefetch.py)

# Runtime dependencies - installed into the build sandbox by
# build/tools/build_native.sh. Keep in sync with that script.
set(TUNEFETCH_DEPS
    customtkinter      # Material 3 widget set
    yt-dlp             # extraction / download engine
    pillow             # cover art handling
    mutagen            # audio tag writing
    imageio-ffmpeg     # bundled ffmpeg binary
    certifi            # CA bundle (TLS fallback #2)
    truststore          # OS trust-store bridge (TLS fallback #3)
)

add_custom_target(tunefetch
    COMMENT "This is informational only - build from the repo root with 'make tunefetch'."
)
