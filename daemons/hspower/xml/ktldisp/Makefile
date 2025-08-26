# Build and install the minimal set of support files needed by the
# stdiosvc KTL front-end.

include ../../Mk.service
include ../../../Mk.instrument
override SYSNAM = kss/$(INSTRUMENT)/$(KTLSERVICE)/xml/ktldisp
override VERNUM = 1.0


FILES = headers.timestamp
CLEAN += $(wildcard *.h) $(wildcard *.tsv)

DATSUB = $(KTLSERVICE)
RELDAT = CoeffMap.tsv KeywordMeta.tsv TableMap.tsv

INCSUB = $(KTLSERVICE)
RELINC = inst_msgs.h inst_kw_ids.h

$(RELDAT) : headers.timestamp
$(RELINC) : headers.timestamp

OUR_XML     = ..
HEADER_DEPS = Makefile $(wildcard $(OUR_XML)/*xml)


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

headers: headers.timestamp

headers.timestamp: $(HEADER_DEPS)
	$(RELDIR)/bin/ktlxml2fiord -s $(KTLSERVICE) -i $(OUR_XML) -o .
	@touch $@
