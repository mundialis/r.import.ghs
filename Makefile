MODULE_TOPDIR = ../..

PGM = r.import.ghs

ETCFILES = tindex_ghs_built_geojson

include $(MODULE_TOPDIR)/include/Make/Script.make
include $(MODULE_TOPDIR)/include/Make/Python.make

default: script
