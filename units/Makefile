# Every unit in this directory: make (both boards), make test, make clean, make dist.
# make dist collects the unit files as dist/<board>-<Bundle>.unt with units.json (sizes, sha256, commit).
UNITS := $(patsubst %/Makefile,%,$(wildcard */Makefile))

all test clean describe arm32 aarch64:
	@set -e; for u in $(UNITS); do $(MAKE) -C $$u $@; done

dist: all
	python3 -I ../tools/dist.py $(UNITS)

.PHONY: all test clean describe arm32 aarch64 dist
