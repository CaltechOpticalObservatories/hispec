# KTLXML definition of the keywords associated with this service.
#

include ../../Mk.instrument
include ../Mk.service

override SYSNAM = kss/$(INSTRUMENT)/$(KTLSERVICE)/xml
override VERNUM = 1.0

MAKEFLAGS += -j4
SUBST_STRICT = True

DEF_DIR = ../def

DISPATCHERS = $(DEF_DIR)/rspec.defs
SUBSYSTEM = $(DISPATCHERS:$(DEF_DIR)/%.defs=%)
DISP_XML = $(SUBSYSTEM:%=%_dispatcher.xml)
OWENV_XML = $(SUBSYSTEM:%=%_owenv.xml)

# HSOWENV_DISP_XML = hsowenvDispatcher1.xml
# OWENV_XML = OWENV.xml

# OWENV_DEFS = $(wildcard *.defs)
# OWENV_XML = $(OWENV_DEFS:disp%.defs=OWENV%.xml)
# OWENV_XML = OWENV.xml

KTLXML_FAMILY_SERVICE = $(KTLSERVICE)
KTLXML_DEPS = Makefile ../Mk.service index.xml

# XML_SIN_IN = $(wildcard *.xml.sin)
# XML_SIN_OUT = $(XML_SIN_IN:%.sin=%)

RELDAT = index.xml messages.xml keyword_ids.xml
RELDAT +=  $(DISP_XML) $(OWENV_XML)
DATSUB = $(KTLSERVICE)/xml

# SIN_IN = $(wildcard *.sin)
# SIN_OUT = $(SIN_IN:%.sin=%)

FILES = $(RELDAT)
PREFILES = $(FILES)
PREINSTALL = $(PREFILES)

# DIRS = configs dtune ktldisp
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

WAPP = $(RELDIR)/bin/wapp +w

# $(OWENV_XML): OWENV%.xml: OWENV.xml.in disp%.defs $(KTLXML_DEPS)
# 	$(WAPP) -F -f disp$*.defs -DKTLSERVICE=$(KTLSERVICE) $< $@

$(DISP_XML): %_dispatcher.xml: $(DEF_DIR)/%.defs
	$(WAPP) -DRELDIR="$(RELDIR)" -f $(DEF_DIR)/$*.defs ./dispatcher.xml.sin $@

$(OWENV_XML): %_owenv.xml: $(DEF_DIR)/%.defs
	$(WAPP) -DRELDIR="$(RELDIR)" -f $(DEF_DIR)/$*.defs ./owenv.xml.sin $@

index.xml: index.xml.sin $(DISPATCHERS)
	$(WAPP) -DKTLSERVICE=$(KTLSERVICE) -DSUBSYSTEMS="$(SUBSYSTEM)" ./index.xml.sin $@