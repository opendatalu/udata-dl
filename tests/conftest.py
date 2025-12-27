"""Pytest configuration and shared fixtures"""

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir)


@pytest.fixture
def sample_dataset_response():
    """Sample API response for datasets"""
    return {
        "data": [
            {
                "id": "dataset-1",
                "title": "Test Dataset 1",
                "slug": "test-dataset-1",
                "description": "A test dataset",
                "created_at": "2023-01-01T00:00:00",
                "last_modified": "2023-01-01T00:00:00",
                "owner": {
                    "first_name": "John",
                    "last_name": "Schmit",
                    "slug": "john-schmit"
                },
                "resources": [
                    {
                        "id": "resource-1",
                        "title": "Test File 1",
                        "url": "https://example.com/file-1.csv",
                        "format": "csv",
                        "type": "main",
                        "filetype": "remote"
                    },
                    {
                        "id": "resource-2",
                        "title": "Test File 2",
                        "url": "https://example.com/file-2.json",
                        "format": "json",
                        "type": "main",
                        "filetype": "remote"
                    }
                ]
            },
            {
                "id": "dataset-2",
                "title": "Test Dataset 2",
                "slug": "test-dataset-2",
                "description": "Another test dataset",
                "created_at": "2023-01-02T00:00:00",
                "last_modified": "2023-01-02T00:00:00",
                "owner": {
                    "first_name": "John",
                    "last_name": "Schmit",
                    "slug": "john-schmit"
                },
                "resources": [
                    {
                        "id": "resource-3",
                        "title": "Test File 3",
                        "url": "https://example.com/file-3.pdf",
                        "format": "pdf",
                        "type": "main",
                        "filetype": "remote"
                    }
                ]
            }
        ],
        "page": 1,
        "page_size": 20,
        "total": 2,
        "next_page": None,
        "previous_page": None
    }


@pytest.fixture
def empty_dataset_response():
    """Empty API response for datasets"""
    return {
        "data": [],
        "page": 1,
        "page_size": 20,
        "total": 0,
        "next_page": None,
        "previous_page": None
    }


@pytest.fixture
def paginated_dataset_response_page1():
    """First page of paginated API response"""
    return {
        "data": [
            {
                "id": "dataset-1",
                "title": "Dataset Page 1",
                "slug": "dataset-page-1",
                "description": "Dataset on page 1",
                "created_at": "2023-01-01T00:00:00",
                "last_modified": "2023-01-01T00:00:00",
                "owner": {
                    "first_name": "John",
                    "last_name": "Schmit",
                    "slug": "john-schmit"
                },
                "resources": [
                    {
                        "id": "resource-1",
                        "title": "File from page 1",
                        "url": "https://example.com/page1.csv",
                        "format": "csv",
                        "type": "main",
                        "filetype": "remote"
                    }
                ]
            }
        ],
        "page": 1,
        "page_size": 1,
        "total": 2,
        "next_page": "https://data.public.lu/api/1/datasets/?page=2",
        "previous_page": None
    }


@pytest.fixture
def paginated_dataset_response_page2():
    """Second page of paginated API response"""
    return {
        "data": [
            {
                "id": "dataset-2",
                "title": "Dataset Page 2",
                "slug": "dataset-page-2",
                "description": "Dataset on page 2",
                "created_at": "2023-01-02T00:00:00",
                "last_modified": "2023-01-02T00:00:00",
                "owner": {
                    "first_name": "John",
                    "last_name": "Schmit",
                    "slug": "john-schmit"
                },
                "resources": [
                    {
                        "id": "resource-2",
                        "title": "File from page 2",
                        "url": "https://example.com/page2.json",
                        "format": "json",
                        "type": "main",
                        "filetype": "remote"
                    }
                ]
            }
        ],
        "page": 2,
        "page_size": 1,
        "total": 2,
        "next_page": None,
        "previous_page": "https://data.public.lu/api/1/datasets/?page=1"
    }


@pytest.fixture
def dataset_response_with_checksums():
    """API response with checksum data"""
    return {
        "data": [
            {
                "id": "dataset-1",
                "title": "Test Dataset with Checksums",
                "slug": "test-dataset-checksums",
                "description": "Dataset with checksum info",
                "created_at": "2023-01-01T00:00:00",
                "last_modified": "2023-01-01T00:00:00",
                "owner": {
                    "first_name": "John",
                    "last_name": "Schmit",
                    "slug": "john-schmit"
                },
                "resources": [
                    {
                        "id": "resource-1",
                        "title": "File with SHA1",
                        "url": "https://example.com/file-1.csv",
                        "format": "csv",
                        "type": "main",
                        "filetype": "remote",
                        "checksum": {
                            "type": "sha1",
                            "value": "da39a3ee5e6b4b0d3255bfef95601890afd80709"  # SHA1 of empty string
                        }
                    },
                    {
                        "id": "resource-2",
                        "title": "File with SHA256",
                        "url": "https://example.com/file-2.json",
                        "format": "json",
                        "type": "main",
                        "filetype": "remote",
                        "checksum": {
                            "type": "sha256",
                            "value": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
                        }
                    }
                ]
            }
        ],
        "page": 1,
        "page_size": 20,
        "total": 1,
        "next_page": None,
        "previous_page": None
    }


@pytest.fixture
def organization_response():
    """Sample organization API response"""
    return {
        "id": "test-org-id",
        "slug": "test-org",
        "name": "Test Organization",
        "description": "A test organization",
        "created_at": "2023-01-01T00:00:00",
        "last_modified": "2023-01-01T00:00:00",
        "page": "https://data.public.lu/en/organizations/test-org/",
        "uri": "https://data.public.lu/api/1/organizations/test-org/",
    }


@pytest.fixture
def single_dataset_response():
    """Sample single dataset API response (from /datasets/{id}/)"""
    return {
        "id": "dataset-123",
        "title": "Daily Meteorological Parameters",
        "slug": "daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590",
        "description": "Daily weather data from Luxembourg Findel Airport",
        "created_at": "2023-01-01T00:00:00",
        "last_modified": "2023-01-01T00:00:00",
        "organization": {
            "id": "test-org-id",
            "slug": "test-org",
            "name": "Test Organization",
            "page": "https://data.public.lu/en/organizations/test-org/",
        },
        "resources": [
            {
                "id": "resource-1",
                "title": "Meteorological Data 2023",
                "url": "https://example.com/meteo-2023.csv",
                "format": "csv",
                "type": "main",
                "filetype": "remote",
                "checksum": {
                    "type": "sha1",
                    "value": "da39a3ee5e6b4b0d3255bfef95601890afd80709"
                }
            },
            {
                "id": "resource-2",
                "title": "Meteorological Data 2022",
                "url": "https://example.com/meteo-2022.csv",
                "format": "csv",
                "type": "main",
                "filetype": "remote"
            }
        ]
    }
