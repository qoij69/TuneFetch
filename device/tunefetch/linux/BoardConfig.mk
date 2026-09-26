# ============================================================
#  BoardConfig.mk  -  tunefetch_linux
# ============================================================
# Per-target packaging flags, read by build/tools/build_native.sh
# at compile time. Edit this file to change how the linux
# artifact is packaged - you shouldn't need to touch the build
# scripts themselves.

TARGET_ARCH      := x86_64
TARGET_PACKAGE   := TuneFetch

PYI_BIN_NAME     := TuneFetch
# --windowed has no effect on Linux - there's no console/GUI
# subsystem split the way Windows/macOS have - so it's left empty.
PYI_WINDOWED_ARGS :=
PYI_ICON_FILE    :=
