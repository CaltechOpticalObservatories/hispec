# 1-Wire environmental sensor (OW-ENV) contorl and telemetry for the HISPEC rack: temperature, humidity, dew point, humidex and head index readout

include ../Mk.instrument
include ./Mk.service

override SYSNAM = kss/$(INSTRUMENT)/$(KTLSERVICE)
override VERNUM = 1.0


DIRS = config dispatcher xml


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
