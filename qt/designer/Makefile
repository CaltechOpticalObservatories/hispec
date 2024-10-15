# KPF GUI components created via Qt Designer.

include ../../Mk.instrument

override SYSNAM = kss/$(INSTRUMENT)/qt/designer/
override VERNUM = 1.0

# DESIGNER = Main.ui FIU.ui SpectrographStatus.ui TipTilt.ui ExpMeter.ui
DESIGNER = Main.ui SPEC.ui
SANITIZED = $(DESIGNER:%.ui=%_sanitized.ui)
SINITIZED = $(SANITIZED:%=%.sin)
TRANSLATED = $(DESIGNER:%.ui=%.py)

RELLIB = __init__.py $(TRANSLATED)
LIBSUB = python/$(INSTRUMENT)Qt

RELDAT = $(wildcard *.png)
DATSUB = $(INSTRUMENT)/images

FILES = $(SANITIZED) $(SINITIZED) $(TRANSLATED)


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

design:
	designer-qt5 $(DESIGNER)


# The pyuic4 script is in the PyQt-devel (or similar) package on
# RedHat linux systems.

$(TRANSLATED): %.py: %_sanitized.ui
	pyuic5 $^ --output $@


# prefix *.png with @RELDIR@/data/@DATSUB/

$(SINITIZED): %_sanitized.ui.sin: %.ui
	$(SED) 's/<pixmap>\(.*\).png<\/pixmap>/<pixmap>@RELDIR@\/data\/@DATSUB@\/\1.png<\/pixmap>/' < $^ > $@ || $(RM) $@
