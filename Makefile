SKILL_DIR := .trae/skills/tangshan-yizhong-history
QUESTION ?= 唐山一中是什么时候建立的？
OUTPUT ?=
PDF ?=

.PHONY: install rebuild query ask export-json

install:
	$(MAKE) -C $(SKILL_DIR) install PDF="$(PDF)"

rebuild:
	$(MAKE) -C $(SKILL_DIR) rebuild

query:
	$(MAKE) -C $(SKILL_DIR) query QUESTION="$(QUESTION)"

ask:
	$(MAKE) -C $(SKILL_DIR) ask QUESTION="$(QUESTION)"

export-json:
	$(MAKE) -C $(SKILL_DIR) export-json QUESTION="$(QUESTION)" OUTPUT="$(OUTPUT)"
