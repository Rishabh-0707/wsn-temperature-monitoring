CONTIKI_PROJECT = sink_node
all: $(CONTIKI_PROJECT)
-include ../../.runtime/contiki.mk
CONTIKI ?= $(HOME)/contiki-ng
MAKE_ROUTING = MAKE_ROUTING_RPL_LITE
MAKE_MAC = MAKE_MAC_CSMA
include $(CONTIKI)/Makefile.include
