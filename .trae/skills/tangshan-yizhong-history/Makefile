PYTHON ?= .venv/bin/python
QUESTION ?= 唐山一中是什么时候建立的？
PDF ?=
OUTPUT ?=

.PHONY: install rebuild query ask export-json

install:
	bash ./install.sh $(PDF)

rebuild:
	$(PYTHON) ./build_index.py

query:
	$(PYTHON) ./query_index.py "$(QUESTION)"

ask:
	$(PYTHON) ./ask.py "$(QUESTION)"

export-json:
	$(PYTHON) ./export_json.py "$(QUESTION)" $(if $(OUTPUT),--output "$(OUTPUT)",)
