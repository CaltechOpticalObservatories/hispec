# KTL client libraries and configuration for HISPEC power control.


include ./Mk.service
include ../Mk.instrument
override SYSNAM = kss/$(INSTRUMENT)/$(KTLSERVICE)
override VERNUM = 1.0


DIRS = config xml


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
