# Variables
SHELL:=/bin/bash
PROJECT := sensorpush
VERSION := 1.0.0
IMAGE_NAME := sensorpush-python
COMPOSE_FILE := compose.yml
GIT_HASH ?= $(shell git log --format="%h" -n 1)
VENV = .venv
UV_PYTHON = uv run python
UV_PIP = uv pip
UV_PIP_COMPILE = uv pip compile
UV_PIP_SYNC = uv pip sync

# Assume uv, uvx, and ruff are installed
UV := $(shell command -v uv)
UVX := $(shell command -v uvx)

# If uv is not found, print an error message and exit
ifeq ($(UV),)
  $(error "uv is required but not found.")
endif

# If uvx is not found, print an error message and exit
ifeq ($(UVX),)
  $(error "uvx is required but not found.")
endif

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
#LINT_CMD = uvx ruff check --fix
LINT_CMD = uvx ruff check
FMT_CMD = uvx ruff format

.DEFAULT_GOAL := help

.PHONY: help
help: ## Display help information about available rules
	@echo "$(GREEN)Available rules:$(RESET)"
	@grep -E '^[a-zA-Z0-9_-]+:.*##' $(MAKEFILE_LIST) | \
	awk -v cyan="$(CYAN)" -v reset="$(RESET)" 'BEGIN {FS = ":.*##"}; {printf "- %s%s%s\n    %s\n\n", cyan, $$1, reset, $$2}'

.PHONY: check-require
check-require: ## Check if required programs are installed
	@echo "Project Name: $(PROJECT)"
	@echo "Project Version: $(VERSION)"
	@echo ""

	@echo "Checking the programs required for the build are installed..."
	@uv run python --version >/dev/null 2>&1 || (echo "ERROR: python is required."; exit 1)
	@uv --version >/dev/null 2>&1 || (echo "ERROR: uv is required."; exit 1)
	@uvx --version >/dev/null 2>&1 || (echo "ERROR: uvx is required."; exit 1)
	@uvx ruff --version >/dev/null 2>&1 || (echo "ERROR: ruff (uv tool) is required."; exit 1)
	@echo ""

	@echo "'python', 'uv', 'uvx', and 'ruff' are installed."
	@echo ""

	@uv run python --version
	@uv --version
	@uvx --version
	@uvx ruff --version


all: init compile-requirements sync-requirements build ## Setup environment and install dependencies
	@echo "Running target: all"

init: check-require ## Create a virtual environment
	@echo "Running target: init"
	@if [ ! -d $(VENV) ]; then \
		echo "Virtual environment does not exist, creating new virtual environment ..."; \
		uv venv $(VENV); \
	fi

	@echo "Installing requirements into virtual environment..."
	@$(MAKE) compile-requirements
	@$(MAKE) sync-requirements
	@echo "Virtual environment setup complete."

.PHONY: compile-requirements
compile-requirements: ## pip-compile Python requirement files
	@echo "Running target: compile-requirements"
	@$(UV_PIP_COMPILE) -o $(REQUIREMENTS_TXT) $(REQUIREMENTS_IN)
	@$(UV_PIP_COMPILE) -o $(DEV_REQUIREMENTS_TXT) $(DEV_REQUIREMENTS_IN)

.PHONY: sync-requirements
sync-requirements: ## pip-sync Python modules with virtual environment
	@echo "Running target: sync-requirements"
	@$(UV_PIP_SYNC) $(DEV_REQUIREMENTS_TXT)

.PHONY: test
test: ## Run unit tests
	@echo "Running target: test"
	$(TEST_CMD)

.PHONY: lint
lint: ## Run linting to check code style
	@echo "Running target: lint"
	$(LINT_CMD)

.PHONY: fmt
fmt: ## Run linting to check code style
	@echo "Running target: fmt"
	$(FMT_CMD)

build: init ## Build the Docker image
	@echo "Running target: build"
	docker build -t $(IMAGE_NAME) ./app

.PHONY: up
up: ## Create and start the Docker Compose services
	@echo "Running target: up"
	docker compose -f $(COMPOSE_FILE) -p $(PROJECT) up -d

.PHONY: start
start: ## Start the Docker Compose services
	@echo "Running target: start"
	docker compose -f $(COMPOSE_FILE) -p $(PROJECT) start

.PHONY: stop
stop: ## Stop the Docker Compose services
	@echo "Running target: stop"
	docker compose -f $(COMPOSE_FILE) -p $(PROJECT) stop

.PHONY: down
down: ## Stop and remove the Docker Compose services
	@echo "Running target: down"
	docker compose -f $(COMPOSE_FILE) -p $(PROJECT) down

.PHONY: create-k8s-deployment
create-k8s-deployment: ## Create k8s deployment
	@echo "Running target: create-k8s-deployment"
	$(UV_PYTHON) ./annotate_elastic_apm.py -m "Created application deployment"
	#kubectl apply -f sensorpush_deployment.yaml

.PHONY: delete-k8s-deployment
delete-k8s-deployment: ## Delete k8s deployment
	@echo "Running target: delete-k8s-deployment"
	@$(UV_PYTHON) ./annotate_elastic_apm.py -m "Deleted application deployment"
	#kubectl delete -f sensorpush_deployment.yaml

.PHONY: clean
clean: ## Clean up virtual environment and other generated files
	@echo "Running target: clean"
	@if [ -d $(VENV) ]; then \
		echo "Removing existing virtual environment ..."; \
		rm -rf $(VENV); \
	fi

	@echo "Removing generated files..."
	@find . -type d -name '__pycache__' -exec rm -r {} +
	@find . -type f -name '*.pyc' -exec rm -f {} +
	@find . -type f -name '*.pyo' -exec rm -f {} +
	@find . -type f -name '*.log' -exec rm -f {} +
	@find . -type f -name '*.egg-info' -exec rm -rf {} +
	@find . -type f -name '*.dist-info' -exec rm -rf {} +
