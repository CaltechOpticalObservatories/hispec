# Config files for the KTL dispatcher.

include ../Mk.service
include ../../Mk.instrument
override SYSNAM = kss/$(INSTRUMENT)/$(KTLSERVICE)/config
override VERNUM = 1.0

MAKEFLAGS += -j4
SUBST_STRICT = True

DEF_DIR = ../def

336_DEFS = rspec1
336_CONFIG = $(336_DEFS:%=$(KTLSERVICE)_%.conf)
336_STDIOSVC = $(336_DEFS:%=$(KTLSERVICE)_%_stdiosvc.conf)

224_DEFS = rspec2
224_CONFIG = $(224_DEFS:%=$(KTLSERVICE)_%.conf)
224_STDIOSVC = $(224_DEFS:%=$(KTLSERVICE)_%_stdiosvc.conf)

TEMPLATE_DIR = template
TEMPLATE_IN = hsdewar_model336.conf.in hsdewar_model224.conf.in hsdewar_stdiosvc.conf.in

RELDAT = $(336_CONFIG) $(336_STDIOSVC) $(224_CONFIG) $(224_STDIOSVC)
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

WAPP = $(RELDIR)/bin/wapp -x -We -F

# $(LAKESHORE_STDIOSVC_CONF): stdiosvc_%.conf : stdiosvc.conf.in Makefile
# 	$(WAPP) -DKTLSERVICE=$(KTLSERVICE) -DDISPNUM=$* -DKROOT=$(KROOT) $< $@

$(336_CONFIG): $(KTLSERVICE)_%.conf: $(DEF_DIR)/%.defs ./$(TEMPLATE_DIR)/hsdewar_model336.conf.in
	$(WAPP) -DKROOT=$(KROOT) -DRELDIR=$(RELDIR) -f $(DEF_DIR)/$*.defs ./$(TEMPLATE_DIR)/hsdewar_model336.conf.in $@

$(336_STDIOSVC): $(KTLSERVICE)_%_stdiosvc.conf: $(DEF_DIR)/%.defs ./$(TEMPLATE_DIR)/hsdewar_stdiosvc.conf.in
	$(WAPP) -DKROOT=$(KROOT) -DRELDIR=$(RELDIR) -f $(DEF_DIR)/$*.defs ./$(TEMPLATE_DIR)/hsdewar_stdiosvc.conf.in $@

$(224_CONFIG): $(KTLSERVICE)_%.conf: $(DEF_DIR)/%.defs ./$(TEMPLATE_DIR)/hsdewar_model224.conf.in
	$(WAPP) -DKROOT=$(KROOT) -DRELDIR=$(RELDIR) -f $(DEF_DIR)/$*.defs ./$(TEMPLATE_DIR)/hsdewar_model224.conf.in $@

$(224_STDIOSVC): $(KTLSERVICE)_%_stdiosvc.conf: $(DEF_DIR)/%.defs ./$(TEMPLATE_DIR)/hsdewar_stdiosvc.conf.in
	$(WAPP) -DKROOT=$(KROOT) -DRELDIR=$(RELDIR) -f $(DEF_DIR)/$*.defs ./$(TEMPLATE_DIR)/hsdewar_stdiosvc.conf.in $@