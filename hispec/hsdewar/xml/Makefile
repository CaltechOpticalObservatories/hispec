# KTLXML definition of the keywords associated with this service.
#

include ../Mk.service
include ../../Mk.instrument
override SYSNAM = kss/$(INSTRUMENT)/$(KTLSERVICE)/xml
override VERNUM = 1.0

SUBST_STRICT = True

KTLXML_FAMILY_SERVICE = $(KTLSERVICE)

# Standard Lakeshore dispatcher.

# LAKESHORE_TEMPLATE = $(RELDIR)/data/lakeshore
# LAKESHORE_TEMPLATES = lakeshoreController.xml.in lakeshoreDispatcher.xml.in lakeshoreInput.xml.in lakeshoreOutput.xml.in lakeshoreTemperature.xml.in

# LAKE_DEFS = $(wildcard disp*.defs)
# LCTRL_XML = $(LAKE_DEFS:disp%.defs=lakeshoreController%.xml)
# LDISP_XML = $(LAKE_DEFS:disp%.defs=lakeshoreDispatcher%.xml)

DEF_DIR = ../def

336_DEFS = rspec1
336_DISP_XML = $(336_DEFS:%=%_dispatcher.xml)
336_CTRL_XML = $(336_DEFS:%=%_controller.xml)
336_INPUT_XML = $(336_DEFS:%=%_input.xml)
336_OUTPUT_XML = $(336_DEFS:%=%_output.xml)

224_DEFS = rspec2
224_DISP_XML = $(224_DEFS:%=%_dispatcher.xml)
224_DEV_XML = $(224_DEFS:%=%_device.xml)
224_TEMP_XML = $(224_DEFS:%=%_temperature.xml)

336_DISPATCHERS = $(336_DEFS)
224_DISPATCHERS = $(224_DEFS)

# INPUTS = INA INB INC IND
# INPUT_DEFS = $(INPUTS:%=%.defs)
# INPUT_XML = $(INPUTS:%=%.xml)

# OUTPUTS = OUT1 OUT2
# OUTPUT_DEFS = $(OUTPUTS:%=%.defs)
# OUTPUT_XML = $(OUTPUTS:%=%.xml)


# Combine all of that.

# RELDAT = index.xml messages.xml keyword_ids.xml \
# 	$(LCTRL_XML) $(LDISP_XML) $(INPUT_XML) $(OUTPUT_XML) \

RELDAT = $(336_DISP_XML) $(336_CTRL_XML) $(336_INPUT_XML) $(336_OUTPUT_XML)
RELDAT += $(224_DISP_XML) $(224_DEV_XML) $(224_TEMP_XML)
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

include $(KROOT)/etc/config.mk
################################################################################

WAPP = $(RELDIR)/bin/wapp -x -We -F

# $(LAKESHORE_TEMPLATES): %: $(LAKESHORE_TEMPLATE)/%
# 	$(RM) $@
# 	$(CP) $< $@

# $(INPUT_XML): %.xml: lakeshoreInput.xml.in %.defs $(KTLXML_DEPS)
# 	$(WAPP) -F -f $*.defs -DKTLSERVICE=$(KTLSERVICE) $< $@

$(336_INPUT_XML): %_input.xml: lakeshoreInput.xml.sin $(DEF_DIR)/%.defs $(KTLXML_DEPS)
	$(WAPP) -F -f $(DEF_DIR)/$*.defs -DKTLSERVICE=$(KTLSERVICE) $< $@

# $(OUTPUT_XML): %.xml: lakeshoreOutput.xml.in %.defs $(KTLXML_DEPS)
# 	$(WAPP) -F -f $*.defs -DKTLSERVICE=$(KTLSERVICE) $< $@

$(336_OUTPUT_XML): %_output.xml: lakeshoreOutput.xml.sin $(DEF_DIR)/%.defs $(KTLXML_DEPS)
	$(WAPP) -F -f $(DEF_DIR)/$*.defs -DKTLSERVICE=$(KTLSERVICE) $< $@

# $(LCTRL_XML): lakeshoreController%.xml: lakeshoreController.xml.in disp%.defs $(KTLXML_DEPS)
# 	$(WAPP) -F -f disp$*.defs -DKTLSERVICE=$(KTLSERVICE) $< $@

$(336_DISP_XML): %_dispatcher.xml: lakeshoreDispatcher.xml.sin $(DEF_DIR)/%.defs $(KTLXML_DEPS)
	$(WAPP) -F -f $(DEF_DIR)/$*.defs -DKTLSERVICE=$(KTLSERVICE) $< $@

$(224_DISP_XML): %_dispatcher.xml: lakeshore224Dispatcher.xml.sin $(DEF_DIR)/%.defs $(KTLXML_DEPS)
	$(WAPP) -F -f $(DEF_DIR)/$*.defs -DKTLSERVICE=$(KTLSERVICE) $< $@

$(224_DEV_XML): %_device.xml: lakeshore224Device.xml.sin $(DEF_DIR)/%.defs $(KTLXML_DEPS)
	$(WAPP) -F -f $(DEF_DIR)/$*.defs -DKTLSERVICE=$(KTLSERVICE) $< $@

$(224_TEMP_XML): %_temperature.xml: lakeshore224Temperature.xml.sin $(DEF_DIR)/%.defs $(KTLXML_DEPS)
	$(WAPP) -F -f $(DEF_DIR)/$*.defs -DKTLSERVICE=$(KTLSERVICE) $< $@

# $(LDISP_XML): lakeshoreDispatcher%.xml: lakeshoreDispatcher.xml.in disp%.defs $(KTLXML_DEPS)
# 	$(WAPP) -F -f disp$*.defs -DKTLSERVICE=$(KTLSERVICE) $< $@

$(336_CTRL_XML): %_controller.xml: lakeshoreController.xml.sin $(DEF_DIR)/%.defs $(KTLXML_DEPS)
	$(WAPP) -F -f $(DEF_DIR)/$*.defs -DKTLSERVICE=$(KTLSERVICE) $< $@

index.xml: index.xml.sin
	$(WAPP) -DKTLSERVICE=$(KTLSERVICE) -D336_DISPATCHERS="$(336_DISPATCHERS)" -D224_DISPATCHERS="$(224_DISPATCHERS)" ./index.xml.sin $@