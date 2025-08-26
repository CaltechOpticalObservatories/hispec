# KTL dispatcher and client libraries for start/stop daemon.

include ../Mk.instrument
include ./Mk.service

override SYSNAM = kss/$(INSTRUMENT)/$(KTLSERVICE)
override VERNUM = 1.0

DIRS = xml generated

FILES = $(KTLSERVICE).conf

RELDAT = $(FILES)
DATSUB = $(KTLSERVICE)

INSTALLVARDIRS += $(KROOT)/var/$(KTLSERVICE)

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

KTLSSD=$(RELDIR)/sbin/ktlssd
have_ktlssd=$(shell test -f $(KTLSSD) && echo $(KTLSSD) || echo "")
ifeq "$(have_ktlssd)" ""
$(error Can't build $(KTLSERVICE): ktlssd is not installed in RELDIR/sbin)
endif

$(KTLSERVICE).conf: $(KTLSERVICE).conf.sin Makefile Mk.service

