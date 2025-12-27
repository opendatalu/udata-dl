# Testing Guide for udata-dl

This document describes the testing strategy and how to run tests for the udata-dl project.

## Test Overview

The test suite includes:
- **Unit tests**: Fast, isolated tests with mocked dependencies (28 tests)
- **Integration tests**: Tests against the real data.public.lu API (6 tests)
- **Code coverage**: Currently at 90% for unit tests

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Shared pytest fixtures
├── test_downloader.py       # Unit tests for downloader module (16 tests)
├── test_cli.py              # Unit tests for CLI interface (12 tests)
└── test_integration.py      # Integration tests with real API (6 tests)
```

## Running Tests

### Prerequisites

Install development dependencies:

```bash
# Using pip
pip install -e ".[dev]"

# Or using make
make install-dev
```

### Quick Test Commands

```bash
# Run unit tests only (default, fast)
pytest
# or
make test

# Run integration tests (requires network)
pytest -m integration
# or
make test-integration

# Run all tests (unit + integration)
pytest -m ""
# or
make test-all

# Run with coverage report
pytest --cov=udata_dl --cov-report=html
# or
make coverage
```

### Running Specific Tests

```bash
# Run a specific test file
pytest tests/test_downloader.py

# Run a specific test class
pytest tests/test_downloader.py::TestDataPublicLuDownloader

# Run a specific test
pytest tests/test_downloader.py::TestDataPublicLuDownloader::test_sanitize_filename

# Run with verbose output
pytest -v

# Run with print statements shown
pytest -s
```

## Test Categories

### Unit Tests (28 tests)

Unit tests run quickly and don't require network access. They use mocked HTTP responses.

**Downloader Tests (`test_downloader.py`)**:
- Initialization and configuration
- Filename sanitization
- File hashing (MD5)
- Dataset fetching with pagination
- File downloading with various scenarios
- Sync operations (normal, dry-run, force)
- Error handling

**CLI Tests (`test_cli.py`)**:
- Command-line argument parsing
- Help and version output
- Dry-run mode
- Force download mode
- Custom output directory
- Error handling (API errors, keyboard interrupt)
- Output formatting

### Integration Tests (6 tests)

Integration tests make real API calls to data.public.lu and are slower. They are excluded by default.

**Real API Tests (`test_integration.py`)**:
- Fetching datasets from organization ID `58d3dccfcc765e5b37aaf0e1`
- Downloading real files
- Dry-run with real data
- Error handling for invalid organizations
- Tests with CFL organization

To run only integration tests:
```bash
pytest -m integration -v
```

## Coverage Report

View the HTML coverage report after running tests:

```bash
pytest --cov=udata_dl --cov-report=html
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

## Test Fixtures

Shared fixtures in `conftest.py`:
- `temp_dir`: Temporary directory for test files
- `sample_dataset_response`: Mock API response with datasets
- `empty_dataset_response`: Mock empty API response
- `paginated_dataset_response_page1/page2`: Mock paginated responses

## Continuous Integration

For CI/CD pipelines, use:

```bash
# Run unit tests only (fast, no network required)
pytest --cov=udata_dl --cov-report=xml

# Run all tests including integration
pytest -m "" --cov=udata_dl --cov-report=xml
```

## Writing New Tests

### Adding Unit Tests

1. Add test functions to `test_downloader.py` or `test_cli.py`
2. Use the `@responses.activate` decorator for mocking HTTP calls
3. Use fixtures from `conftest.py` for common test data

Example:
```python
@responses.activate
def test_new_feature(temp_dir, sample_dataset_response):
    responses.add(
        responses.GET,
        "https://data.public.lu/api/1/datasets/",
        json=sample_dataset_response,
        status=200
    )
    # Your test code here
```

### Adding Integration Tests

1. Add test functions to `test_integration.py`
2. Mark slow tests with `@pytest.mark.slow`
3. Handle potential API changes gracefully

Example:
```python
@pytest.mark.slow
def test_real_api_feature(temp_dir):
    # Test against real API
    pass
```

## Troubleshooting

### Tests Fail Due to Network Issues

Integration tests require network access. If they fail:
1. Check your internet connection
2. Verify data.public.lu is accessible
3. Run unit tests only: `pytest` (integration tests excluded by default)

### Import Errors

Make sure the package is installed in development mode:
```bash
pip install -e ".[dev]"
```

### Coverage Not Generated

Ensure pytest-cov is installed:
```bash
pip install pytest-cov
```

## Test Configuration

Test configuration is in `pytest.ini`:
```ini
[pytest]
markers =
    integration: marks tests as integration tests (may be slow, requires network)
    slow: marks tests as slow running tests

addopts = -v --cov=udata_dl --cov-report=term-missing --cov-report=html -m "not integration"
```

This configuration:
- Runs unit tests by default (excludes integration tests)
- Generates coverage reports automatically
- Shows verbose output

## Makefile Commands

Quick reference for Makefile commands:

```bash
make help              # Show all available commands
make install           # Install package
make install-dev       # Install with dev dependencies
make test              # Run unit tests
make test-unit         # Run unit tests explicitly
make test-integration  # Run integration tests
make test-all          # Run all tests
make coverage          # Generate coverage report
make clean             # Clean build artifacts
```

## Best Practices

1. **Run unit tests before committing**: `pytest`
2. **Check coverage**: Aim for >80% coverage
3. **Test edge cases**: Empty responses, errors, timeouts
4. **Keep tests fast**: Mock external dependencies
5. **Use descriptive test names**: `test_download_file_skip_existing`
6. **Run integration tests periodically**: Verify API compatibility

## Example Test Session

```bash
# 1. Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# 2. Run unit tests
pytest

# 3. Check coverage
pytest --cov=udata_dl --cov-report=html
open htmlcov/index.html

# 4. Run integration tests (optional)
pytest -m integration -v

# 5. Run specific test during development
pytest tests/test_downloader.py::TestDataPublicLuDownloader::test_sanitize_filename -v
```
