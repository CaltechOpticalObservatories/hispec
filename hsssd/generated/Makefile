
include ../Mk.service

override SYSNAM = util/$(KTLSERVICE)/generated
override VERNUM = 1.0

TSV_FILES = $(notdir $(wildcard $(RELDIR)/data/ktlssd/*.tsv))
DOTH_FILES = $(notdir $(wildcard $(RELDIR)/include/ktlssd/*.h))

RELDAT = $(TSV_FILES) $(KTLSERVICE).attr
RELINC = $(notdir $(wildcard $(RELDIR)/include/ktlssd/*.h))

FILES = $(RELDAT) $(RELINC)

DATSUB = $(KTLSERVICE)
INCSUB = $(KTLSERVICE)

XMLHERE     = ../xml
HEADER_DEPS = Makefile $(wildcard $(XMLHERE)/*xml)

DTUNE_SYMLINK = $(KTLSERVICE)

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

$(TSV_FILES) : % : $(RELDIR)/data/ktlssd/%
	echo "use: ktlssd" > $@

$(DOTH_FILES) : % : $(RELDIR)/include/ktlssd/%
	test -f $@ && chmod +w $@ || true
	$(CP) $^ $@

# Build a .attr file. The first dependency is satisfied by automatic
# rules triggered by setting DTUNE_SYMLINK.
# We add a dependency on ktlssd's .attr file, because if it updates, we'd
# better update our version.

$(KTLSERVICE).attr: lib$(KTLSERVICE)_keyword$(SHLIB_SUFFIX) $(RELDIR)/data/ktlssd/ktlssd.attr ../xml/*.xml
	$(RELDIR)/bin/kattr -t -l . -x ../xml -f $(KTLSERVICE)
