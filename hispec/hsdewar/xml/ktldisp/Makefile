# Build and install generated support files for the dispatcher front-end.

include ../../../Mk.instrument
include ../../Mk.service

override SYSNAM = kss/$(INSTRUMENT)/$(KTLSERVICE)/xml/ktldisp
override VERNUM = 1.0


FILES = headers.timestamp
CLEAN += $(wildcard *.h) $(wildcard *.tsv) $(wildcard *.cfg)

DATSUB = $(KTLSERVICE)
RELDAT = CoeffMap.tsv KeywordMeta.tsv TableMap.tsv

INCSUB = $(KTLSERVICE)
RELINC = inst_msgs.h inst_kw_ids.h

XMLHERE = ..
HEADER_DEPS = Makefile $(wildcard $(XMLHERE)/*xml)


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

$(RELDAT) : headers.timestamp
$(RELINC) : headers.timestamp

headers: headers.timestamp

headers.timestamp: $(HEADER_DEPS) $(RELDIR)/bin/ktlxml2fiord
	$(RELDIR)/bin/ktlxml2fiord -s $(KTLSERVICE) -i $(XMLHERE) -o .
	@touch $@
