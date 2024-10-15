# KTL dispatcher and configuration for the 1-Wire environmental sensor.
include ../Mk.service
include ../../Mk.instrument

override SYSNAM = kss/$(INSTRUMENT)/$(KTLSERVICE)/dispatcher
override VERNUM = 1.0

SUBST_STRICT = True

RELSBIN = hsowenvd
FILES = $(RELSBIN)

DIRS = hsOWENV

################################################################################
# KROOT boilerplate:
# Include general make rules, using default values for the key environment
# variables if they are not already set.

ifndef KROOT
	KROOT = /kroot
endif

ifndef RELNAM
	RELNAM = default
endif

ifndef RELDIR
	RELDIR = $(KROOT)/rel/$(RELNAM)
endif

include $(KROOT)/etc/config.mk
################################################################################
