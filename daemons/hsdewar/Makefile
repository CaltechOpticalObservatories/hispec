# Environmental control and telemetry for the HISPEC dewar: temperature
# control, vacuum gague readings, etc.

include ../Mk.instrument
include ./Mk.service

override SYSNAM = kss/$(INSTRUMENT)/$(KTLSERVICE)
override VERNUM = 1.0

SUBST_STRICT = True

DIRS = config dispatcher xml


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
