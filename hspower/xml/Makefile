# KTLXML definition of the keywords associated with this service.
#

include ../../Mk.instrument
include ../Mk.service

override SYSNAM = kss/$(INSTRUMENT)/$(KTLSERVICE)/xml
override VERNUM = 1.0

MAKEFLAGS += -j4
SUBST_STRICT = True

DEF_DIR = ../def
PDU_DEFS = rspec1

HSPOWER_STRIP_XML = $(PDU_DEFS:%=%_strip.xml)
HSPOWER_OUTLETS_XML = $(PDU_DEFS:%=%_outlets.xml)
HSPOWER_DISP_XML = $(PDU_DEFS:%=%_dispatcher.xml)

SUBSYSTEMS = $(PDU_DEFS)

KTLXML_FAMILY_SERVICE = $(KTLSERVICE)
KTLXML_DEPS = Makefile ../Mk.service index.xml

TEMPLATE_DIR = template

RELDAT = $(HSPOWER_STRIP_XML) $(HSPOWER_OUTLETS_XML) $(HSPOWER_DISP_XML) 
RELDAT += index.xml messages.xml keyword_ids.xml
DATSUB = $(KTLSERVICE)/xml

FILES = $(RELDAT)
PREFILES = $(FILES)
PREINSTALL = $(PREFILES)

DIRS = dtune ktldisp


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

WAPP = $(RELDIR)/bin/wapp -x -We -F

$(HSPOWER_STRIP_XML): %_strip.xml: $(DEF_DIR)/%.defs
	$(WAPP) -DRELDIR="$(RELDIR)" -f $(DEF_DIR)/$*.defs ./$(TEMPLATE_DIR)/hspower_strip.xml.in $@

$(HSPOWER_OUTLETS_XML): %_outlets.xml: $(DEF_DIR)/%.defs
	$(WAPP) -DRELDIR="$(RELDIR)" -f $(DEF_DIR)/$*.defs ./$(TEMPLATE_DIR)/hspower_outlets.xml.in $@

$(HSPOWER_DISP_XML): %_dispatcher.xml: $(DEF_DIR)/%.defs
	$(WAPP) -DRELDIR="$(RELDIR)" -f $(DEF_DIR)/$*.defs ./$(TEMPLATE_DIR)/hspower_dispatcher.xml.in $@

index.xml: index.xml.sin
	$(WAPP) -DKTLSERVICE=$(KTLSERVICE) -DSUBSYSTEMS="$(SUBSYSTEMS)" ./index.xml.sin $@
