# Config files for the KTL dispatcher.

include ../../Mk.instrument
include ../Mk.service

override SYSNAM = kss/$(INSTRUMENT)/$(KTLSERVICE)/dispatcher
override VERNUM = 1.0


SUBST_STRICT = True

RELSBIN = hs_lakeshored
FILES = $(RELSBIN)

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
