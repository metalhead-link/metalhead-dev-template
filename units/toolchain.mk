# Where the SDK and the cross compilers are, for every unit's Makefile (before the SDK's unit.mk).
# Override any of them on the command line: make SDK=../../metalhead-unit-sdk CROSSPATH=...
UNITS_ROOT := $(patsubst %/,%,$(dir $(lastword $(MAKEFILE_LIST))))
SDK ?= $(UNITS_ROOT)/../sdk

# BeagleBone Black: arm-none-eabi-gcc from the PATH, with the libgcc and newlib libm the firmware
# links: the ARM (not Thumb) v5te hard-float multilib. Thumb ones can't be linked into a
# position-independent unit. (The SDK's defaults are macOS paths.)
ARM_GCC := $(shell command -v arm-none-eabi-gcc 2>/dev/null)
ifneq ($(ARM_GCC),)
ARM_FLAGS := -marm -march=armv5te+fp -mfloat-abi=hard
CROSSPATH ?= $(patsubst %/,%,$(dir $(ARM_GCC)))
LIBGCC_arm32 ?= $(shell $(ARM_GCC) $(ARM_FLAGS) -print-libgcc-file-name)
LIBM_arm32 ?= $(shell $(ARM_GCC) $(ARM_FLAGS) -print-file-name=libm.a)
endif

# Raspberry Pi 5: aarch64-none-elf-gcc from the PATH
AARCH64_GCC := $(shell command -v aarch64-none-elf-gcc 2>/dev/null)
ifneq ($(AARCH64_GCC),)
CROSSPATH_AARCH64 ?= $(patsubst %/,%,$(dir $(AARCH64_GCC)))
endif

# make test on Linux, where there is gcc and maybe no clang
HOST_CC ?= $(if $(shell command -v clang 2>/dev/null),clang,gcc)
HOST_CXX ?= $(if $(shell command -v clang++ 2>/dev/null),clang++,g++)
