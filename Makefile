# Makefile - Laboratorio de procesos e hilos, version PYTHON (Linux)
#
# Python no se compila: `make` valida la sintaxis de todos los modulos y
# `make clean` elimina la cache de bytecode. Requiere Python 3.8+ en Linux.

PYTHON := python3

.PHONY: all check clean

all: check

check:
	@for f in src/*.py scripts/*.py; do \
		$(PYTHON) -m py_compile "$$f" || exit 1; \
	done
	@echo "Sintaxis OK"

clean:
	@find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "Cache de bytecode eliminada"
