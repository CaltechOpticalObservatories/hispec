# KTL client library installation.

include ../../Mk.service
include ../../../Mk.instrument

override SYSNAM = kss/$(INSTRUMENT)/$(KTLSERVICE)/xml/dtune
override VERNUM = 1.0


DTUNE_SYMLINK = $(KTLSERVICE)

RELDAT = $(KTLSERVICE).attr
DATSUB = $(KTLSERVICE)

FILES = $(RELDAT)


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

# Build a .attr file. The first dependency is satisfied by automatic
# rules triggered by setting DTUNE_SYMLINK.

$(KTLSERVICE).attr: lib$(KTLSERVICE)_keyword$(SHLIB_SUFFIX) ../*.xml
	$(RELDIR)/bin/kattr -t -l . -x .. -f $(KTLSERVICE)
