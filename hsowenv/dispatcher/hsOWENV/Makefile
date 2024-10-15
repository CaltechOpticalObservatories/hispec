include ../../../Mk.instrument
include ../../Mk.service


override SYSNAM = kss/$(INSTRUMENT)/$(KTLSERVICE)/dispatcher/hsOWENV
override VERNUM = 1.0
override ENABLE_PYTHON2 = False

RELLIB = __init__.py owenv.py snmp.py
LIBSUB = python/hsOWENV

FILES = owenv.py

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

include $(RELDIR)/etc/defs.mk
################################################################################

ifneq "$(PYTHON3_SHLIB_EXT)" ""
	ENABLE_PYTHON3 = True
endif

################################################################################
include $(RELDIR)/etc/rules.mk
################################################################################
