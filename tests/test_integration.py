"""Integration tests against real data.public.lu API

These tests make actual API calls and can be slow.
Run with: pytest tests/test_integration.py -v
"""

import pytest
from pathlib import Path

from udata_dl.downloader import DataPublicLuDownloader


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestRealAPI:
    """Integration tests against real API"""

    def test_get_real_organization_datasets(self, temp_dir):
        """Test fetching datasets from a real organization"""
        # Using the organization ID provided by the user
        org_id = "58d3dccfcc765e5b37aaf0e1"

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        datasets = downloader.get_datasets(org_id)

        # Should get at least some datasets
        assert isinstance(datasets, list)
        # Don't assert on exact count as it may change

        if datasets:
            # Verify structure of first dataset
            dataset = datasets[0]
            assert "id" in dataset
            assert "title" in dataset
            assert "slug" in dataset
            assert "resources" in dataset

            # Verify resources structure
            resources = dataset.get("resources", [])
            if resources:
                resource = resources[0]
                assert "url" in resource
                # URL should be present
                assert resource["url"]

    @pytest.mark.slow
    def test_download_single_file_from_real_org(self, temp_dir):
        """Test downloading a single file from real organization"""
        org_id = "58d3dccfcc765e5b37aaf0e1"

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        datasets = downloader.get_datasets(org_id)

        if not datasets:
            pytest.skip("No datasets available for this organization")

        # Find first dataset with resources
        dataset_with_resources = None
        for dataset in datasets:
            if dataset.get("resources"):
                dataset_with_resources = dataset
                break

        if not dataset_with_resources:
            pytest.skip("No datasets with resources found")

        # Get first resource
        resource = dataset_with_resources["resources"][0]
        resource_url = resource.get("url")

        if not resource_url:
            pytest.skip("No URL available for resource")

        # Download the file
        dataset_slug = dataset_with_resources["slug"]
        filename = f"test_download_{resource.get('format', 'file')}"
        filepath = temp_dir / org_id / dataset_slug / filename

        success, message = downloader.download_file(resource_url, filepath)

        # Should successfully download or skip if exists
        assert success is True
        assert filepath.exists()

    @pytest.mark.slow
    def test_dry_run_sync_real_org(self, temp_dir):
        """Test dry run sync with real organization"""
        org_id = "58d3dccfcc765e5b37aaf0e1"

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))

        # This should not download anything, just show what would be downloaded
        downloader.sync_organization(org_id, dry_run=True)

        # Verify no files were actually downloaded
        org_dir = temp_dir / org_id
        if org_dir.exists():
            files = list(org_dir.rglob("*"))
            files = [f for f in files if f.is_file()]
            assert len(files) == 0

    def test_api_error_handling(self, temp_dir):
        """Test handling of invalid organization ID"""
        invalid_org = "nonexistent-organization-12345"

        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        datasets = downloader.get_datasets(invalid_org)

        # Should return empty list for non-existent org
        assert isinstance(datasets, list)
        assert len(datasets) == 0


class TestCFLOrganization:
    """Tests specific to CFL organization"""

    @pytest.fixture
    def cfl_org_id(self):
        """CFL organization identifier"""
        return "societe-nationale-des-chemins-de-fer-luxembourgeois"

    def test_get_cfl_datasets(self, temp_dir, cfl_org_id):
        """Test fetching CFL datasets"""
        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        datasets = downloader.get_datasets(cfl_org_id)

        assert isinstance(datasets, list)
        # CFL should have some datasets

        if datasets:
            # Check structure
            for dataset in datasets[:3]:  # Check first 3
                assert "id" in dataset
                assert "slug" in dataset

    @pytest.mark.slow
    def test_cfl_dry_run(self, temp_dir, cfl_org_id):
        """Test dry run with CFL organization"""
        downloader = DataPublicLuDownloader(output_dir=str(temp_dir))
        downloader.sync_organization(cfl_org_id, dry_run=True)

        # Should complete without errors
        # No files should be downloaded in dry run mode
        org_dir = temp_dir / cfl_org_id
        if org_dir.exists():
            files = list(org_dir.rglob("*"))
            files = [f for f in files if f.is_file()]
            assert len(files) == 0
