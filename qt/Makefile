# Graphical user interface for KPF, based on PyQt.

include ../Mk.instrument

override SYSNAM = kss/$(INSTRUMENT)/qt/
override VERNUM = 1.0

DIRS = designer

RELBIN = hispec_gui
FILES = $(RELBIN)


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
