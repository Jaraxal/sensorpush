# Variables
SHELL:=/bin/bash
COMPOSE_FILE := compose.yml
PROJECT := sensorpush
IMAGE_NAME := sensorpush-python
GIT_HASH ?= $(shell git log --format="%h" -n 1)
VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
PIP_COMPILE = $(VENV)/bin/pip-compile
PIP_SYNC = $(VENV)/bin/pip-sync

# Assumes the use of pyenv for managing Python versions
PYENV_ROOT := $(HOME)/.pyenv
PATH := $(PYENV_ROOT)/shims:$(PYENV_ROOT)/bin:$(PATH)

# Define color variables
GREEN := $(shell tput setaf 2)
CYAN := $(shell tput setaf 6)
RESET := $(shell tput sgr0)

# Requirements files
REQUIREMENTS_IN = ./app/requirements/prod.in
REQUIREMENTS_TXT = ./app/requirements/prod.txt
DEV_REQUIREMENTS_IN = ./app/requirements/dev.in
DEV_REQUIREMENTS_TXT = ./app/requirements/dev.txt

# Directories
TEST_DIR = tests
SRC_DIR = ./app

# Commands for testing and linting
TEST_CMD = ./$(VENV)/bin/pytest $(TEST_DIR)
LINT_CMD = ./$(VENV)/bin/flake8 --exclude $(VENV) $(SRC_DIR)
FMT_CMD = ./$(VENV)/bin/black $(SRC_DIR)

PYTHON_CMD := $(shell command -v python || command -v python3)

# If python is not found, print an error message and exit
ifeq ($(PYTHON_CMD),)
  $(error "Python is required but not found.")
endif

# Get Python version
PYTHON_VERSION := $(shell $(PYTHON_CMD) --version 2>&1 | cut -d' ' -f2)

# Split Python version into major, minor, and patch components
PYTHON_MAJOR_VERSION := $(shell echo $(PYTHON_VERSION) | cut -d. -f1)
PYTHON_MINOR_VERSION := $(shell echo $(PYTHON_VERSION) | cut -d. -f2)
PYTHON_PATCH_VERSION := $(shell echo $(PYTHON_VERSION) | cut -d. -f3)

# Check if Python minor version is >= 11
ifeq ($(shell [ $(PYTHON_MINOR_VERSION) -ge 11 ] && echo 1 || echo 0), 0)
  $(error "Python version must be 3.11 or higher. Detected: $(PYTHON_VERSION)")
endif

.DEFAULT_GOAL := help
.PHONY: help check-python-version all init install install-dev test lint fmt build compile-requirements compile-dev-requirements sync-requirements sync-dev-requriements up start stop down 

## Default Target: Display help information about available rules
help:
	@echo "$$(tput setaf 2)Available rules:$$(tput sgr0)";sed -ne"/^## /{h;s/.*//;:d" -e"H;n;s/^## /---/;td" -e"s/:.*//;G;s/\\n## /===/;s/\\n//g;p;}" ${MAKEFILE_LIST}|awk -F === -v n=$$(tput cols) -v i=4 -v a="$$(tput setaf 6)" -v z="$$(tput sgr0)" '{printf"- %s%s%s\n",a,$$1,z;m=split($$2,w,"---");l=n-i;for(j=1;j<=m;j++){l-=length(w[j])+1;if(l<= 0){l=n-i-length(w[j])-1;}printf"%*s%s\n\n",-i," ",w[j];}}'

## Check the Python version
check-python-version: 
	@echo "Using Python: $(PYTHON)"
	@echo "Python Version: $(PYTHON_VERSION)"

## Setup environment and install dependencies
all: init compile-requirements install
	@echo "Running target: all"

## Create a virtual environment
init: check-python-version
	@echo "Running target: init"
	@if [ -d $(VENV) ]; then \
		echo "Removing existing virtual environment..."; \
		rm -rf $(VENV); \
	fi

	@echo "Creating new virtual environment..."
	$(PYTHON_CMD) -m venv $(VENV)

	@echo "Activating virtual environment and installing requirements..."
	@$(PIP) install --upgrade pip setuptools wheel pip-tools
	@echo "Virtual environment setup complete."

## Compile the requirements.txt from requirements.in
compile-requirements:
	@echo "Running target: compile-requirements"
	$(PIP_COMPILE) $(REQUIREMENTS_IN)

## Compile the dev-requirements.txt from dev-requirements.in (which includes requirements.txt)
compile-dev-requirements: compile-requirements
	@echo "Running target: compile-dev-requirements"
	$(PIP_COMPILE) $(DEV_REQUIREMENTS_IN)

## Sync dependencies from compiled requirements.txt
sync-requirements:
	@echo "Running target: sync-requirements"
	$(PIP_SYNC) $(REQUIREMENTS_TXT)

## Sync development dependencies from compiled dev-requirements.txt
sync-dev-requirements:
	@echo "Running target: sync-dev-requirements"
	$(PIP_SYNC) $(DEV_REQUIREMENTS_TXT)

## Run unit tests
test:
	@echo "Running target: test"
	$(TEST_CMD)

## Run linting to check code style
lint:
	@echo "Running target: lint"
	$(LINT_CMD)

## Run linting to check code style
fmt:
	@echo "Running target: fmt"
	$(FMT_CMD)

## Build the Docker image
build: init
	@echo "Running target: build"
	docker build -t $(IMAGE_NAME) ./app

## Create and start the Docker Compose services
up: 
	@echo "Running target: up"
	docker compose -f $(COMPOSE_FILE) -p $(PROJECT) up -d

## Start the Docker Compose services
start:
	@echo "Running target: start"
	docker compose -f $(COMPOSE_FILE) -p $(PROJECT) start

## Stop the Docker Compose services
stop:
	@echo "Running target: stop"
	docker compose -f $(COMPOSE_FILE) -p $(PROJECT) stop

## Stop and remove the Docker Compose services
down:
	@echo "Running target: down"
	docker compose -f $(COMPOSE_FILE) -p $(PROJECT) down

.PHONY: clean
clean: ## Clean up virtual environment and other generated files
	@echo "Running target: clean"
	@rm -rf $(VENV)
	@find . -type d -name '__pycache__' -exec rm -r {} +
	@find . -type f -name '*.pyc' -exec rm -f {} +
	@find . -type f -name '*.pyo' -exec rm -f {} +
	@find . -type f -name '*.log' -exec rm -f {} +
	@find . -type f -name '*.egg-info' -exec rm -rf {} +
	@find . -type f -name '*.dist-info' -exec rm -rf {} +

.PHONY: lint
lint: ## Lint the Python source code
	@echo "Running target: lint"
	@$(LINT_CMD)

.PHONY: fmt
fmt: ## Format the Python source code
	@echo "Running target: fmt"
	@$(FMT_CMD)