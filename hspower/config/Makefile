# Config files for the KTL dispatcher.

include ../Mk.service
include ../../Mk.instrument

override SYSNAM = kss/$(INSTRUMENT)/$(KTLSERVICE)/config
override VERNUM = 1.0

MAKEFLAGS += -j4
SUBST_STRICT = True

DEF_DIR = ../def
PDU_DEFS = rspec1

HSPOWER_CONFIG = $(PDU_DEFS:%=$(KTLSERVICE)_%.conf)
HSPOWER_STDIOSVC = $(PDU_DEFS:%=$(KTLSERVICE)_%_stdiosvc.conf)

TEMPLATE_DIR = template

RELDAT = $(HSPOWER_CONFIG) $(HSPOWER_STDIOSVC)
DATSUB = $(KTLSERVICE)

# FILES = $(RELDAT) $(UPS_TEMPLATE_IN) $(PDU_TEMPLATE_IN)
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

# $(TEMPLATE_IN): %: $(TEMPLATE_DIR)/%
# 	$(RM) $@
# 	$(CP) $^ $@

# $(PDU_TEMPLATE_IN): %: $(PDU_TEMPLATES)/%
# 	$(RM) $@
# 	$(CP) $^ $@

WAPP = $(RELDIR)/bin/wapp -x -We -F

$(HSPOWER_CONFIG): $(KTLSERVICE)_%.conf: $(DEF_DIR)/%.defs ./$(TEMPLATE_DIR)/hspower.conf.in
	$(WAPP) -DKROOT=$(KROOT) -DRELDIR=$(RELDIR) -f $(DEF_DIR)/$*.defs ./$(TEMPLATE_DIR)/hspower.conf.in $@

$(HSPOWER_STDIOSVC): $(KTLSERVICE)_%_stdiosvc.conf: $(DEF_DIR)/%.defs ./$(TEMPLATE_DIR)/hspower_stdiosvc.conf.in
	$(WAPP) -DKROOT=$(KROOT) -DRELDIR=$(RELDIR) -f $(DEF_DIR)/$*.defs ./$(TEMPLATE_DIR)/hspower_stdiosvc.conf.in $@
