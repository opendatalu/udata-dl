"""Tests for the downloader module"""

import pytest
import responses
from pathlib import Path
from unittest.mock import Mock, patch

from udata_dl.downloader import DataPublicLuDownloader


class TestDataPublicLuDownloader:
    """Test suite for DataPublicLuDownloader class"""

    def test_init(self, temp_dir):
        """Test downloader initialization"""
        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        assert downloader.output_dir == temp_dir
        assert downloader.console is not None
        assert downloader.session is not None

    def test_sanitize_filename(self, temp_dir):
        """Test filename sanitization"""
        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))

        # Test various problematic characters
        assert downloader.sanitize_filename("file<name>.csv") == "file_name_.csv"
        assert downloader.sanitize_filename("file:name.csv") == "file_name.csv"
        assert downloader.sanitize_filename('file"name".csv') == "file_name_.csv"
        assert downloader.sanitize_filename("file/name.csv") == "file_name.csv"
        assert downloader.sanitize_filename("file\\name.csv") == "file_name.csv"
        assert downloader.sanitize_filename("file|name.csv") == "file_name.csv"
        assert downloader.sanitize_filename("file?name.csv") == "file_name.csv"
        assert downloader.sanitize_filename("file*name.csv") == "file_name.csv"

        # Test normal filename
        assert downloader.sanitize_filename("normal-file_name.csv") == "normal-file_name.csv"

    def test_get_file_hash_nonexistent(self, temp_dir):
        """Test getting hash of nonexistent file"""
        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        result = downloader.get_file_hash(temp_dir / "nonexistent.txt")
        assert result is None

    def test_get_file_hash_existing(self, temp_dir):
        """Test getting hash of existing file"""
        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))

        # Create a test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")

        # Get SHA1 hash (default)
        hash1 = downloader.get_file_hash(test_file)
        assert hash1 is not None
        assert len(hash1) == 40  # SHA1 hash length

        # Verify same content produces same hash
        hash2 = downloader.get_file_hash(test_file)
        assert hash1 == hash2

        # Verify different content produces different hash
        test_file.write_text("different content")
        hash3 = downloader.get_file_hash(test_file)
        assert hash3 != hash1

    def test_get_file_hash_different_algorithms(self, temp_dir):
        """Test getting hash with different algorithms"""
        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))

        # Create a test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")

        # Test different algorithms
        sha1_hash = downloader.get_file_hash(test_file, "sha1")
        assert len(sha1_hash) == 40

        sha256_hash = downloader.get_file_hash(test_file, "sha256")
        assert len(sha256_hash) == 64

        md5_hash = downloader.get_file_hash(test_file, "md5")
        assert len(md5_hash) == 32

        # Verify different algorithms produce different hashes
        assert sha1_hash != sha256_hash != md5_hash

    @responses.activate
    def test_get_datasets_single_page(self, temp_dir, sample_dataset_response):
        """Test fetching datasets with single page"""
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/",
            json=sample_dataset_response,
            status=200
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        datasets = downloader.get_datasets("test-org")

        assert len(datasets) == 2
        assert datasets[0]["slug"] == "test-dataset-1"
        assert datasets[1]["slug"] == "test-dataset-2"

    @responses.activate
    def test_get_datasets_empty(self, temp_dir, empty_dataset_response):
        """Test fetching datasets with empty response"""
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/",
            json=empty_dataset_response,
            status=200
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        datasets = downloader.get_datasets("test-org")

        assert len(datasets) == 0

    @responses.activate
    def test_get_datasets_pagination(
        self, temp_dir, paginated_dataset_response_page1, paginated_dataset_response_page2
    ):
        """Test fetching datasets with pagination"""
        # Mock first page
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/",
            json=paginated_dataset_response_page1,
            status=200
        )

        # Mock second page
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/",
            json=paginated_dataset_response_page2,
            status=200
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        datasets = downloader.get_datasets("test-org")

        assert len(datasets) == 2
        assert datasets[0]["slug"] == "dataset-page-1"
        assert datasets[1]["slug"] == "dataset-page-2"

    @responses.activate
    def test_get_datasets_api_error(self, temp_dir):
        """Test fetching datasets with API error"""
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/",
            json={"error": "Not found"},
            status=404
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        datasets = downloader.get_datasets("nonexistent-org")

        assert len(datasets) == 0

    @responses.activate
    def test_download_file_success(self, temp_dir):
        """Test successful file download"""
        file_content = b"test file content"
        responses.add(
            responses.GET,
            "https://example.com/test.csv",
            body=file_content,
            status=200,
            headers={"content-length": str(len(file_content))}
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        filepath = temp_dir / "test.csv"

        success, message = downloader.download_file("https://example.com/test.csv", filepath)

        assert success is True
        assert "downloaded" in message
        assert filepath.exists()
        assert filepath.read_bytes() == file_content

    @responses.activate
    def test_download_file_redownload_without_checksum(self, temp_dir):
        """Test re-downloading existing file when no checksum is available"""
        old_content = b"old content"
        new_content = b"new content"

        # Create existing file
        filepath = temp_dir / "existing.csv"
        filepath.write_bytes(old_content)

        # Mock download (no checksum provided, so should re-download)
        responses.add(
            responses.GET,
            "https://example.com/existing.csv",
            body=new_content,
            status=200,
            headers={"content-length": str(len(new_content))}
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        success, message = downloader.download_file("https://example.com/existing.csv", filepath)

        assert success is True
        assert "downloaded" in message
        # Verify file was re-downloaded with new content
        assert filepath.read_bytes() == new_content

    @responses.activate
    def test_download_file_force(self, temp_dir):
        """Test forcing download of existing file"""
        old_content = b"old content"
        new_content = b"new content"

        # Create existing file
        filepath = temp_dir / "test.csv"
        filepath.write_bytes(old_content)

        # Mock download
        responses.add(
            responses.GET,
            "https://example.com/test.csv",
            body=new_content,
            status=200,
            headers={"content-length": str(len(new_content))}
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        success, message = downloader.download_file(
            "https://example.com/test.csv",
            filepath,
            force=True
        )

        assert success is True
        assert "downloaded" in message
        assert filepath.read_bytes() == new_content

    @responses.activate
    def test_download_file_error(self, temp_dir):
        """Test download with network error"""
        responses.add(
            responses.GET,
            "https://example.com/test.csv",
            status=500
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        filepath = temp_dir / "test.csv"

        success, message = downloader.download_file("https://example.com/test.csv", filepath)

        assert success is False
        assert "error" in message
        assert not filepath.exists()

    @responses.activate
    def test_download_file_creates_directories(self, temp_dir):
        """Test that download creates parent directories"""
        file_content = b"test content"
        responses.add(
            responses.GET,
            "https://example.com/test.csv",
            body=file_content,
            status=200,
            headers={"content-length": str(len(file_content))}
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        filepath = temp_dir / "deep" / "nested" / "dirs" / "test.csv"

        success, message = downloader.download_file("https://example.com/test.csv", filepath)

        assert success is True
        assert filepath.exists()
        assert filepath.parent.exists()

    @responses.activate
    def test_get_organization(self, temp_dir, organization_response):
        """Test fetching organization details"""
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/organizations/test-org/",
            json=organization_response,
            status=200
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        org = downloader.get_organization("test-org")

        assert org is not None
        assert org["slug"] == "test-org"
        assert org["name"] == "Test Organization"

    @responses.activate
    def test_get_organization_error(self, temp_dir):
        """Test fetching organization with error"""
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/organizations/invalid/",
            status=404
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        org = downloader.get_organization("invalid")

        assert org is None

    @responses.activate
    def test_sync_organization_dry_run(self, temp_dir, organization_response, sample_dataset_response):
        """Test sync in dry run mode"""
        # Mock organization endpoint
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/organizations/test-org/",
            json=organization_response,
            status=200
        )

        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/",
            json=sample_dataset_response,
            status=200
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        downloader.sync_organization("test-org", dry_run=True)

        # Verify no files were created
        org_dir = temp_dir / "test-org"
        if org_dir.exists():
            # Check that no actual files were downloaded
            files = list(org_dir.rglob("*"))
            files = [f for f in files if f.is_file()]
            assert len(files) == 0

    @responses.activate
    def test_sync_organization_with_resources(self, temp_dir, organization_response, sample_dataset_response):
        """Test syncing organization with resources"""
        # Mock organization endpoint
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/organizations/test-org/",
            json=organization_response,
            status=200
        )

        # Mock datasets API
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/",
            json=sample_dataset_response,
            status=200
        )

        # Mock file downloads
        responses.add(
            responses.GET,
            "https://example.com/file-1.csv",
            body=b"csv content",
            status=200,
            headers={"content-length": "11"}
        )
        responses.add(
            responses.GET,
            "https://example.com/file-2.json",
            body=b"json content",
            status=200,
            headers={"content-length": "12"}
        )
        responses.add(
            responses.GET,
            "https://example.com/file-3.pdf",
            body=b"pdf content",
            status=200,
            headers={"content-length": "11"}
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        downloader.sync_organization("test-org")

        # Verify files were created
        dataset1_dir = temp_dir / "test-org" / "test-dataset-1"
        dataset2_dir = temp_dir / "test-org" / "test-dataset-2"

        assert dataset1_dir.exists()
        assert dataset2_dir.exists()

        # Check files
        files = list(dataset1_dir.rglob("*.csv")) + list(dataset1_dir.rglob("*.json"))
        assert len(files) == 2

        files = list(dataset2_dir.rglob("*.pdf"))
        assert len(files) == 1

    @responses.activate
    def test_download_file_with_checksum_match(self, temp_dir):
        """Test skipping download when checksum matches"""
        # Create existing file with known content
        filepath = temp_dir / "test.csv"
        filepath.write_bytes(b"")  # Empty file

        # SHA1 of empty string
        checksum = {
            "type": "sha1",
            "value": "da39a3ee5e6b4b0d3255bfef95601890afd80709"
        }

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        success, message = downloader.download_file(
            "https://example.com/test.csv",
            filepath,
            checksum=checksum
        )

        assert success is True
        assert "checksum match" in message

    @responses.activate
    def test_download_file_with_checksum_mismatch(self, temp_dir):
        """Test re-downloading when checksum doesn't match"""
        # Create existing file with different content
        filepath = temp_dir / "test.csv"
        filepath.write_bytes(b"old content")

        # SHA1 of empty string (different from file content)
        checksum = {
            "type": "sha1",
            "value": "da39a3ee5e6b4b0d3255bfef95601890afd80709"
        }

        # Mock download of new file
        responses.add(
            responses.GET,
            "https://example.com/test.csv",
            body=b"",  # Empty content
            status=200,
            headers={"content-length": "0"}
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        success, message = downloader.download_file(
            "https://example.com/test.csv",
            filepath,
            checksum=checksum
        )

        assert success is True
        assert "downloaded" in message
        assert filepath.read_bytes() == b""

    @responses.activate
    def test_sync_organization_deletes_orphaned_files(self, temp_dir, organization_response, sample_dataset_response):
        """Test that orphaned files are deleted"""
        # Create some existing files including an orphan
        org_dir = temp_dir / "test-org" / "test-dataset-1"
        org_dir.mkdir(parents=True)

        (org_dir / "file-1.csv").write_bytes(b"old")
        (org_dir / "file-2.json").write_bytes(b"old")
        (org_dir / "orphaned_file.txt").write_bytes(b"should be deleted")

        # Mock organization endpoint
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/organizations/test-org/",
            json=organization_response,
            status=200
        )

        # Mock datasets API
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/",
            json=sample_dataset_response,
            status=200
        )

        # Mock file downloads
        responses.add(
            responses.GET,
            "https://example.com/file-1.csv",
            body=b"csv content",
            status=200,
            headers={"content-length": "11"}
        )
        responses.add(
            responses.GET,
            "https://example.com/file-2.json",
            body=b"json content",
            status=200,
            headers={"content-length": "12"}
        )
        responses.add(
            responses.GET,
            "https://example.com/file-3.pdf",
            body=b"pdf content",
            status=200,
            headers={"content-length": "11"}
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        downloader.sync_organization("test-org")

        # Verify orphaned file was deleted
        assert not (org_dir / "orphaned_file.txt").exists()

        # Verify expected files still exist
        assert (org_dir / "file-1.csv").exists()
        assert (org_dir / "file-2.json").exists()

    @responses.activate
    def test_sync_organization_with_checksums(self, temp_dir, organization_response, dataset_response_with_checksums):
        """Test syncing with checksum verification"""
        # Mock organization endpoint
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/organizations/test-org/",
            json=organization_response,
            status=200
        )

        # Mock datasets API
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/",
            json=dataset_response_with_checksums,
            status=200
        )

        # Mock file downloads - empty files matching the checksums
        responses.add(
            responses.GET,
            "https://example.com/file-1.csv",
            body=b"",
            status=200,
            headers={"content-length": "0"}
        )
        responses.add(
            responses.GET,
            "https://example.com/file-2.json",
            body=b"",
            status=200,
            headers={"content-length": "0"}
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        downloader.sync_organization("test-org")

        # Verify files were created
        dataset_dir = temp_dir / "test-org" / "test-dataset-checksums"
        assert (dataset_dir / "file-1.csv").exists()
        assert (dataset_dir / "file-2.json").exists()

        # Run sync again - files should be skipped due to checksum match
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/organizations/test-org/",
            json=organization_response,
            status=200
        )
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/",
            json=dataset_response_with_checksums,
            status=200
        )

        downloader.sync_organization("test-org")

        # Files should still exist and have same content
        assert (dataset_dir / "file-1.csv").read_bytes() == b""
        assert (dataset_dir / "file-2.json").read_bytes() == b""

    @responses.activate
    def test_sync_organization_empty(self, temp_dir, organization_response, empty_dataset_response):
        """Test syncing organization with no datasets"""
        # Create a modified organization response for empty-org
        empty_org_response = organization_response.copy()
        empty_org_response["id"] = "empty-org-id"
        empty_org_response["slug"] = "empty-org"
        empty_org_response["name"] = "Empty Organization"

        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/organizations/empty-org/",
            json=empty_org_response,
            status=200
        )

        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/",
            json=empty_dataset_response,
            status=200
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        downloader.sync_organization("empty-org")

        # Should complete without error
        org_dir = temp_dir / "empty-org"
        assert not org_dir.exists() or len(list(org_dir.rglob("*"))) == 0

    @responses.activate
    def test_get_dataset(self, temp_dir, single_dataset_response):
        """Test fetching a single dataset"""
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590/",
            json=single_dataset_response,
            status=200
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        dataset = downloader.get_dataset("daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590")

        assert dataset is not None
        assert dataset["slug"] == "daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590"
        assert dataset["title"] == "Daily Meteorological Parameters"
        assert len(dataset["resources"]) == 2

    @responses.activate
    def test_get_dataset_not_found(self, temp_dir):
        """Test fetching a nonexistent dataset"""
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/nonexistent/",
            json={"error": "Not found"},
            status=404
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        dataset = downloader.get_dataset("nonexistent")

        assert dataset is None

    @responses.activate
    def test_sync_dataset_without_organization(self, temp_dir, single_dataset_response):
        """Test syncing a single dataset without specifying organization"""
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590/",
            json=single_dataset_response,
            status=200
        )

        # Mock file downloads
        responses.add(
            responses.GET,
            "https://example.com/meteo-2023.csv",
            body=b"",
            status=200,
            headers={"content-length": "0"}
        )
        responses.add(
            responses.GET,
            "https://example.com/meteo-2022.csv",
            body=b"csv content",
            status=200,
            headers={"content-length": "11"}
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        downloader.sync_dataset("daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590")

        # Check that files were downloaded in the correct directory structure
        dataset_dir = temp_dir / "test-org" / "daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590"
        assert dataset_dir.exists()
        assert (dataset_dir / "meteo-2023.csv").exists()
        assert (dataset_dir / "meteo-2022.csv").exists()

    @responses.activate
    def test_sync_dataset_with_force(self, temp_dir, single_dataset_response):
        """Test syncing a single dataset with force download"""
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590/",
            json=single_dataset_response,
            status=200
        )

        # Create existing files
        dataset_dir = temp_dir / "test-org" / "daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        existing_file = dataset_dir / "meteo-2023.csv"
        existing_file.write_bytes(b"old content")

        # Mock file downloads (will be called twice with force)
        responses.add(
            responses.GET,
            "https://example.com/meteo-2023.csv",
            body=b"new content",
            status=200,
            headers={"content-length": "11"}
        )
        responses.add(
            responses.GET,
            "https://example.com/meteo-2022.csv",
            body=b"csv content",
            status=200,
            headers={"content-length": "11"}
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        downloader.sync_dataset(
            "daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590",
            force=True
        )

        # Check that files were re-downloaded
        assert dataset_dir.exists()
        assert existing_file.read_bytes() == b"new content"
        assert (dataset_dir / "meteo-2022.csv").exists()

    @responses.activate
    def test_sync_dataset_dry_run(self, temp_dir, single_dataset_response):
        """Test syncing a single dataset in dry run mode"""
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590/",
            json=single_dataset_response,
            status=200
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        downloader.sync_dataset(
            "daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590",
            dry_run=True
        )

        # Check that no files were downloaded
        dataset_dir = temp_dir / "test-org" / "daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590"
        assert not dataset_dir.exists() or not any(dataset_dir.rglob("*.csv"))

    @responses.activate
    def test_sync_dataset_with_checksum_skip(self, temp_dir, single_dataset_response):
        """Test syncing dataset skips files with matching checksums"""
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590/",
            json=single_dataset_response,
            status=200
        )

        # Create existing file with matching checksum (empty file matches the SHA1 in fixture)
        dataset_dir = temp_dir / "test-org" / "daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        existing_file = dataset_dir / "meteo-2023.csv"
        existing_file.write_bytes(b"")  # Empty file has SHA1: da39a3ee5e6b4b0d3255bfef95601890afd80709

        # Mock download for the second file only
        responses.add(
            responses.GET,
            "https://example.com/meteo-2022.csv",
            body=b"csv content",
            status=200,
            headers={"content-length": "11"}
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        downloader.sync_dataset("daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590")

        # First file should still exist with same content (skipped)
        assert existing_file.read_bytes() == b""

        # Second file should be downloaded
        assert (dataset_dir / "meteo-2022.csv").exists()

    @responses.activate
    def test_sync_dataset_deletes_orphaned_files(self, temp_dir, single_dataset_response):
        """Test syncing dataset deletes files no longer in API"""
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590/",
            json=single_dataset_response,
            status=200
        )

        # Create dataset directory with an orphaned file
        dataset_dir = temp_dir / "test-org" / "daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        orphaned_file = dataset_dir / "old-file.csv"
        orphaned_file.write_text("old content")

        # Mock file downloads
        responses.add(
            responses.GET,
            "https://example.com/meteo-2023.csv",
            body=b"",
            status=200,
            headers={"content-length": "0"}
        )
        responses.add(
            responses.GET,
            "https://example.com/meteo-2022.csv",
            body=b"csv content",
            status=200,
            headers={"content-length": "11"}
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        downloader.sync_dataset("daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590")

        # Orphaned file should be deleted
        assert not orphaned_file.exists()

        # New files should exist
        assert (dataset_dir / "meteo-2023.csv").exists()
        assert (dataset_dir / "meteo-2022.csv").exists()

    @responses.activate
    def test_sync_dataset_no_organization(self, temp_dir):
        """Test syncing dataset without organization in API response"""
        dataset_without_org = {
            "id": "dataset-123",
            "title": "Dataset Without Org",
            "slug": "dataset-without-org",
            "description": "A dataset without organization",
            "created_at": "2023-01-01T00:00:00",
            "last_modified": "2023-01-01T00:00:00",
            "organization": None,
            "owner": {
                "first_name": "John",
                "last_name": "Schmit",
                "slug": "john-schmit"
            },
            "resources": []
        }

        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/dataset-without-org/",
            json=dataset_without_org,
            status=200
        )

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        downloader.sync_dataset("dataset-without-org")

        # Should handle gracefully without crash
        # No files should be downloaded since there's no organization
        assert not any((temp_dir).rglob("*.csv"))
