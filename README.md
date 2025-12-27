# udata-dl

A CLI tool to download and synchronize files from udata platforms (data.public.lu and others).

## Features

- Download all files from any udata platform organization
- Support for multiple udata instances (data.public.lu, or any custom instance)
- Organize files by dataset
- Intelligent synchronization with checksum verification:
  - Uses checksums from API when available
  - Re-downloads files without checksums to ensure freshness
  - Only skips downloads when checksums match
- Automatic cleanup: Deletes local files that have been removed from the platform
- Force re-download option
- Dry-run mode to preview downloads
- Progress tracking with rich console output
- No authentication required

## Installation

### Using pipx (Recommended)

```bash
pipx install udata-dl
```

### Using pip

```bash
pip install udata-dl
```

### From source

```bash
git clone <repository-url>
cd udata-dl
pip install .
```

## Usage

### Basic Usage

Download all files from an organization:

```bash
udata-dl societe-nationale-des-chemins-de-fer-luxembourgeois
```

This will download all files to `./societe-nationale-des-chemins-de-fer-luxembourgeois/` organized by dataset.

Download a single dataset:

```bash
udata-dl --dataset daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590
```

This will download only the specified dataset. The organization is automatically determined from the dataset's metadata, and files are saved to the appropriate directory structure.

### Options

```bash
udata-dl [OPTIONS] [ORGANIZATION]
```

**Arguments:**
- `ORGANIZATION`: The identifier (ID or slug) of the organization (required unless `--dataset` is used)

**Options:**
- `-d, --dataset DATASET`: Download only a specific dataset (by ID or slug). **Mutually exclusive with ORGANIZATION.**
- `-o, --output PATH`: Output directory for downloaded files (default: .`)
- `-u, --api-url URL`: Base URL of the udata API (default: `https://data.public.lu/api/1`)
- `-f, --force`: Force download even if files already exist
- `-n, --dry-run`: Show what would be downloaded without actually downloading
- `--version`: Show version and exit
- `--help`: Show help message and exit

**Note:** You must specify either `ORGANIZATION` or `--dataset`, but not both. They are mutually exclusive.

### Examples

Download all datasets from an organization:
```bash
udata-dl societe-nationale-des-chemins-de-fer-luxembourgeois
```

Download a single dataset (organization is auto-detected from dataset metadata):
```bash
udata-dl --dataset daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590
```

Use a different udata instance:
```bash
udata-dl my-organization --api-url https://data.other-instance.org/api/1
```

Use just the domain (will automatically add https and /api/1):
```bash
udata-dl my-organization -u data.other-instance.org
```

Download to a custom directory:
```bash
udata-dl societe-nationale-des-chemins-de-fer-luxembourgeois -o /path/to/data
```

Force re-download all files:
```bash
udata-dl societe-nationale-des-chemins-de-fer-luxembourgeois --force
```

Preview what would be downloaded (dry run):
```bash
udata-dl societe-nationale-des-chemins-de-fer-luxembourgeois --dry-run
```

Download a single dataset in dry-run mode:
```bash
udata-dl --dataset my-dataset-slug --dry-run
```

### Synchronization

The tool supports synchronization for both organizations and individual datasets:

1. **First run**: Downloads all files to your local directory
2. **Subsequent runs**:
   - Skips files that match the checksum from the API
   - Re-downloads files without checksums to ensure they're up to date
   - **Deletes local files** that no longer exist in the API
3. **Force mode**: Re-downloads everything regardless of checksums

**Automatic cleanup**:
- Files removed from udata are automatically deleted locally
- Empty dataset directories are cleaned up
- This keeps your local mirror in perfect sync

To keep your local copy in sync, simply run the same command periodically:

```bash
udata-dl societe-nationale-des-chemins-de-fer-luxembourgeois
```

## File Organization

Files are organized in the following structure:

```
output_directory/
└── organization-slug/
    ├── dataset-slug-1/
    │   ├── file1.csv
    │   ├── file2.pdf
    │   └── ...
    ├── dataset-slug-2/
    │   ├── file1.json
    │   └── ...
    └── ...
```

The tool automatically fetches the organization's slug from the API and uses it for the folder name, making the structure more readable and URL-friendly.

## Finding Organizations and Datasets

### Finding Organizations

To find an organization on data.public.lu:

1. Visit [data.public.lu](https://data.public.lu)
2. Navigate to the organization's page
3. You can use either:
   - The **organization slug** from the URL: `https://data.public.lu/fr/organizations/{slug}/`
   - The **organization ID** (also works)

The tool accepts both formats and will automatically resolve the slug for folder naming.

Example organization slugs from data.public.lu:
- `societe-nationale-des-chemins-de-fer-luxembourgeois` - CFL (Luxembourg Railways)
- `administration-de-la-gestion-de-leau` - Water Management Administration
- `statec-institut-national-de-la-statistique-et-des-etudes-economiques-du-grand-duche-de-luxembourg` - STATEC

### Finding Datasets

To find a specific dataset on data.public.lu:

1. Visit [data.public.lu](https://data.public.lu)
2. Navigate to the dataset's page
3. Use the **dataset slug** from the URL: `https://data.public.lu/fr/datasets/{slug}/`

Example dataset slug:
- `daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590` - Daily weather data from Luxembourg Findel Airport

You can download a dataset directly without specifying its organization:
```bash
udata-dl --dataset daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590
```

The tool will automatically determine the organization from the dataset metadata and use it for folder structure.

## Requirements

- Python 3.8 or higher
- Internet connection

## Dependencies

- `click` - Command-line interface framework
- `requests` - HTTP library for API calls
- `rich` - Beautiful terminal output

## Development

### Setup Development Environment

```bash
git clone <repository-url>
cd udata-dl
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

### Project Structure

```
udata-dl/
├── udata_dl/
│   ├── __init__.py      # Package initialization
│   ├── cli.py           # CLI interface
│   └── downloader.py    # Download and sync logic
├── tests/
│   ├── __init__.py      # Test package
│   ├── conftest.py      # Shared fixtures
│   ├── test_downloader.py  # Downloader tests
│   ├── test_cli.py      # CLI tests
│   └── test_integration.py # Integration tests
├── pyproject.toml       # Project configuration
├── pytest.ini           # Pytest configuration
├── README.md            # This file
└── LICENSE              # MIT License
```

### Running Tests

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run unit tests (fast, no network required):

```bash
pytest
```

Run with coverage report:

```bash
pytest --cov=udata_dl --cov-report=html
```

Run integration tests (requires network, slower):

```bash
pytest -m integration
```

Run all tests including integration:

```bash
pytest -m ""
```

Run specific test file:

```bash
pytest tests/test_downloader.py -v
```

For detailed testing information, see [TESTING.md](TESTING.md).

## API Reference

The tool uses the data.public.lu API v1:
- API Base: `https://data.public.lu/api/1`
- Endpoint: `GET /datasets/`
- Documentation: [https://data.public.lu/api/1/swagger.json](https://data.public.lu/api/1/swagger.json)

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions:
- Create an issue on the GitHub repository
- Check existing issues for solutions

