# Instrument software for the Keck Planet Finder (KPF).

include ./Mk.instrument

override SYSNAM = kss/$(INSTRUMENT)/
override VERNUM = 1.0


DIRS = init.d
# hardware servers
# DIRS += hsowenv hspower hsdewar
DIRS += hsowenv hsdewar

#  won't build until after other services are installed.
DIRS += 




## qt needs Qt.
# DIRS += qt

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
