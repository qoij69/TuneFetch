# ============================================================
#  TuneFetch top-level build file
#  Don't call this directly - source build/envsetup.sh, run
#  'lunch' to pick a target, then 'make tunefetch' (or 'm', 'mka').
# ============================================================

PRODUCT ?= $(TUNEFETCH_PRODUCT)
VARIANT ?= $(TUNEFETCH_VARIANT)

.PHONY: tunefetch clean help

tunefetch:
ifeq ($(PRODUCT),)
	@echo "You haven't chosen a target product yet."
	@echo "Try:  source build/envsetup.sh && lunch"
	@exit 1
endif
ifeq ($(PRODUCT),allproducts)
	@bash build/tools/setup_ci.sh
else
	@bash build/tools/build_native.sh $(PRODUCT) $(VARIANT)
endif

clean:
	rm -rf out .tunefetch-build-venv

help:
	@echo "Usage:"
	@echo "  source build/envsetup.sh"
	@echo "  lunch"
	@echo "  make tunefetch     (or: m / mka / mm)"
	@echo
	@echo "Other targets: clean"
