include ../Mk.service
include ../../Mk.instrument

override SYSNAM = kss/$(INSTRUMENT)/$(KTLSERVICE)/config
override VERNUM = 1.0

DEF_DIR = ../def

DISPATCHERS = $(DEF_DIR)/rspec.defs
DISP_CONF = $(DISPATCHERS:$(DEF_DIR)/%.defs=$(KTLSERVICE)_%.conf)
STDIOSVC_CONF = $(DISPATCHERS:$(DEF_DIR)/%.defs=$(KTLSERVICE)_%_stdiosvc.conf)

TEMPLATE_DIR = template
TEMPLATE_IN = ktlservice_dispnum.conf.in ktlservice_dispnum_stdiosvc.conf.in

RELDAT = $(DISP_CONF) $(STDIOSVC_CONF)
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

$(DISP_CONF): $(KTLSERVICE)_%.conf: $(DEF_DIR)/%.defs ./$(TEMPLATE_DIR)/ktlservice_dispnum.conf.in
	$(WAPP) -DKROOT=$(KROOT) -DRELDIR=$(RELDIR) -f $(DEF_DIR)/$*.defs ./$(TEMPLATE_DIR)/ktlservice_dispnum.conf.in $@

$(STDIOSVC_CONF): $(KTLSERVICE)_%_stdiosvc.conf: $(DEF_DIR)/%.defs ./$(TEMPLATE_DIR)/ktlservice_dispnum_stdiosvc.conf.in
	$(WAPP) -DKROOT=$(KROOT) -DRELDIR=$(RELDIR) -f $(DEF_DIR)/$*.defs ./$(TEMPLATE_DIR)/ktlservice_dispnum_stdiosvc.conf.in $@