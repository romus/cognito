PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
PIPX ?= pipx
PACKAGE_NAME := cognito

.PHONY: venv install test run-help pipx-install pipx-uninstall

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -e .[dev]

test:
	$(PYTEST)

run-help:
	$(VENV)/bin/cognito --help

pipx-install:
	$(PIPX) install --force .

pipx-uninstall:
	$(PIPX) uninstall $(PACKAGE_NAME)
