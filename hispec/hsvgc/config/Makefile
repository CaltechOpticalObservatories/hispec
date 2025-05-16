# Config files for the KTL dispatcher.

include ../Mk.service
include ../../Mk.instrument
override SYSNAM = kss/$(INSTRUMENT)/$(KTLSERVICE)/config
override VERNUM = 1.0

MAKEFLAGS += -j4
SUBST_STRICT = True

DEF_DIR = ../def

VGC503_DEFS = fei
VGC503_CONFIG = $(VGC503_DEFS:%=$(KTLSERVICE)_%.conf)
VGC503_STDIOSVC = $(VGC503_DEFS:%=$(KTLSERVICE)_%_stdiosvc.conf)

TEMPLATE_DIR = template
TEMPLATE_IN = hsvgc_vgc503.conf.in hsvgc_stdiosvc.conf.in

RELDAT = $(VGC503_CONFIG) $(VGC503_STDIOSVC)
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

$(VGC503_CONFIG): $(KTLSERVICE)_%.conf: $(DEF_DIR)/%.defs ./$(TEMPLATE_DIR)/hsvgc_vgc503.conf.in
	$(WAPP) -DKROOT=$(KROOT) -DRELDIR=$(RELDIR) -f $(DEF_DIR)/$*.defs ./$(TEMPLATE_DIR)/hsvgc_vgc503.conf.in $@

$(VGC503_STDIOSVC): $(KTLSERVICE)_%_stdiosvc.conf: $(DEF_DIR)/%.defs ./$(TEMPLATE_DIR)/hsvgc_stdiosvc.conf.in
	$(WAPP) -DKROOT=$(KROOT) -DRELDIR=$(RELDIR) -f $(DEF_DIR)/$*.defs ./$(TEMPLATE_DIR)/hsvgc_stdiosvc.conf.in $@