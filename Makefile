.PHONY: help install install-dev test test-unit test-integration test-all coverage clean lint format

help:
	@echo "Available commands:"
	@echo "  make install          - Install package"
	@echo "  make install-dev      - Install package with dev dependencies"
	@echo "  make test             - Run unit tests (default)"
	@echo "  make test-unit        - Run unit tests only"
	@echo "  make test-integration - Run integration tests (requires network)"
	@echo "  make test-all         - Run all tests"
	@echo "  make coverage         - Run tests with coverage report"
	@echo "  make clean            - Remove build artifacts and cache"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test: test-unit

test-unit:
	pytest

test-integration:
	pytest -m integration -v

test-all:
	pytest -m "" -v

coverage:
	pytest --cov=udata_dl --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
