"""Tests for the CLI module"""

import pytest
import responses
from click.testing import CliRunner
from pathlib import Path

from udata_dl.cli import main, build_api_url


class TestBuildApiUrl:
    """Test suite for build_api_url function"""

    def test_build_api_url_full_url(self):
        """Test with full API URL"""
        url = "https://data.example.org/api/1"
        assert build_api_url(url) == "https://data.example.org/api/1"

    def test_build_api_url_full_url_with_trailing_slash(self):
        """Test with full API URL and trailing slash"""
        url = "https://data.example.org/api/1/"
        assert build_api_url(url) == "https://data.example.org/api/1"

    def test_build_api_url_domain_only(self):
        """Test with domain only"""
        domain = "data.example.org"
        assert build_api_url(domain) == "https://data.example.org/api/1"

    def test_build_api_url_with_https(self):
        """Test with https but no /api/1"""
        url = "https://data.example.org"
        assert build_api_url(url) == "https://data.example.org/api/1"

    def test_build_api_url_with_http(self):
        """Test with http protocol"""
        url = "http://data.example.org"
        assert build_api_url(url) == "http://data.example.org/api/1"

    def test_build_api_url_with_different_api_version(self):
        """Test with different API path"""
        url = "https://data.example.org/api/2"
        assert build_api_url(url) == "https://data.example.org/api/2"


class TestCLI:
    """Test suite for CLI interface"""

    def test_cli_help(self):
        """Test CLI help output"""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "udata" in result.output.lower()
        assert "organization" in result.output.lower()
        assert "api-url" in result.output.lower()

    def test_cli_version(self):
        """Test CLI version output"""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "version" in result.output.lower() or "0.3.0" in result.output

    def test_cli_missing_organization(self):
        """Test CLI with missing organization argument"""
        runner = CliRunner()
        result = runner.invoke(main, [])

        assert result.exit_code != 0
        assert "organization" in result.output.lower() or "missing" in result.output.lower()

    @responses.activate
    def test_cli_basic_sync(self, organization_response, sample_dataset_response):
        """Test basic sync command"""
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

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["test-org"])

            assert result.exit_code == 0
            assert "test-org" in result.output

            # Check files were created
            assert Path("./test-org").exists()

    @responses.activate
    def test_cli_custom_output_dir(self, organization_response, sample_dataset_response):
        """Test CLI with custom output directory"""
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

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["test-org", "-o", "custom_data"])

            assert result.exit_code == 0
            assert Path("custom_data/test-org").exists()

    @responses.activate
    def test_cli_dry_run(self, organization_response, sample_dataset_response):
        """Test CLI dry run mode"""
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

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["test-org", "--dry-run"])

            assert result.exit_code == 0
            assert "dry run" in result.output.lower() or "would download" in result.output.lower()

            # Verify no files were downloaded
            data_dir = Path("data/test-org")
            if data_dir.exists():
                files = list(data_dir.rglob("*"))
                files = [f for f in files if f.is_file()]
                assert len(files) == 0

    @responses.activate
    def test_cli_force_download(self, organization_response, sample_dataset_response):
        """Test CLI force download option"""
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

        # Mock downloads (will be called twice due to force)
        for _ in range(2):
            responses.add(
                responses.GET,
                "https://example.com/file1.csv",
                body=b"csv content",
                status=200,
                headers={"content-length": "11"}
            )
            responses.add(
                responses.GET,
                "https://example.com/file2.json",
                body=b"json content",
                status=200,
                headers={"content-length": "12"}
            )
            responses.add(
                responses.GET,
                "https://example.com/file3.pdf",
                body=b"pdf content",
                status=200,
                headers={"content-length": "11"}
            )

        runner = CliRunner()
        with runner.isolated_filesystem():
            # First sync
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
            result1 = runner.invoke(main, ["test-org"])
            assert result1.exit_code == 0

            # Force sync
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
            result2 = runner.invoke(main, ["test-org", "--force"])
            assert result2.exit_code == 0

    @responses.activate
    def test_cli_empty_organization(self, organization_response, empty_dataset_response):
        """Test CLI with organization that has no datasets"""
        # Create empty organization response
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

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["empty-org"])

            assert result.exit_code == 0
            assert "no datasets" in result.output.lower() or "0" in result.output

    @responses.activate
    def test_cli_api_error(self):
        """Test CLI with API error"""
        # Mock organization endpoint to fail
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/organizations/nonexistent-org/",
            json={"error": "Not found"},
            status=404
        )

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["nonexistent-org"])

            # Should fail gracefully when organization doesn't exist
            assert result.exit_code == 0  # CLI completes but with error message
            assert "error" in result.output.lower() or "could not" in result.output.lower()

    def test_cli_keyboard_interrupt(self, mocker):
        """Test CLI handles keyboard interrupt gracefully"""
        # Mock the downloader to raise KeyboardInterrupt
        mock_downloader = mocker.patch("udata_dl.cli.UdataDownloader")
        mock_instance = mock_downloader.return_value
        mock_instance.sync_organization.side_effect = KeyboardInterrupt()

        runner = CliRunner()
        result = runner.invoke(main, ["test-org"])

        assert result.exit_code == 130
        assert "interrupted" in result.output.lower()

    @responses.activate
    def test_cli_short_options(self, organization_response, sample_dataset_response):
        """Test CLI with short option flags"""
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

        runner = CliRunner()
        with runner.isolated_filesystem():
            # Test -o for output
            result = runner.invoke(main, ["test-org", "-o", "out"])
            assert result.exit_code == 0

            # Test -n for dry-run
            result = runner.invoke(main, ["test-org", "-n"])
            assert result.exit_code == 0

    @responses.activate
    def test_cli_output_formatting(self, organization_response, sample_dataset_response):
        """Test that CLI output contains expected information"""
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

        responses.add(
            responses.GET,
            "https://example.com/file1.csv",
            body=b"csv content",
            status=200,
            headers={"content-length": "11"}
        )
        responses.add(
            responses.GET,
            "https://example.com/file2.json",
            body=b"json content",
            status=200,
            headers={"content-length": "12"}
        )
        responses.add(
            responses.GET,
            "https://example.com/file3.pdf",
            body=b"pdf content",
            status=200,
            headers={"content-length": "11"}
        )

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["test-org"])

            assert result.exit_code == 0
            # Check for dataset information
            assert "Test Dataset 1" in result.output or "test-dataset-1" in result.output
            # Check for completion message
            assert "completed" in result.output.lower() or "summary" in result.output.lower()

    @responses.activate
    def test_cli_custom_api_url(self, organization_response, sample_dataset_response):
        """Test CLI with custom API URL"""
        custom_api_url = "https://custom.data.org/api/1"

        # Mock organization endpoint on custom instance
        responses.add(
            responses.GET,
            f"{custom_api_url}/organizations/my-org/",
            json=organization_response,
            status=200
        )

        # Mock datasets API on custom instance
        responses.add(
            responses.GET,
            f"{custom_api_url}/datasets/",
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

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["my-org", "--api-url", custom_api_url])

            assert result.exit_code == 0
            assert custom_api_url in result.output
            assert Path("./test-org").exists()

    @responses.activate
    def test_cli_single_dataset(self, single_dataset_response):
        """Test CLI with single dataset option"""
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

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["--dataset", "daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590"])

            assert result.exit_code == 0
            assert "Daily Meteorological Parameters" in result.output

            # Check files were created
            assert Path("./test-org/daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590").exists()

    def test_cli_organization_and_dataset_mutually_exclusive(self):
        """Test CLI rejects both organization and dataset together"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, [
                "test-org",
                "--dataset", "my-dataset"
            ])

            assert result.exit_code == 1
            assert "mutually exclusive" in result.output.lower() or "error" in result.output.lower()

    def test_cli_missing_organization_and_dataset(self):
        """Test CLI with neither organization nor dataset"""
        runner = CliRunner()
        result = runner.invoke(main, [])

        assert result.exit_code == 1
        assert "error" in result.output.lower() or "must be specified" in result.output.lower()

    @responses.activate
    def test_cli_dataset_dry_run(self, single_dataset_response):
        """Test CLI with dataset in dry-run mode"""
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590/",
            json=single_dataset_response,
            status=200
        )

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, [
                "--dataset", "daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590",
                "--dry-run"
            ])

            assert result.exit_code == 0
            assert "dry run" in result.output.lower() or "would download" in result.output.lower()

            # Verify no files were downloaded
            dataset_dir = Path("data/test-org/daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590")
            if dataset_dir.exists():
                files = list(dataset_dir.rglob("*"))
                files = [f for f in files if f.is_file()]
                assert len(files) == 0

    @responses.activate
    def test_cli_dataset_not_found(self):
        """Test CLI with nonexistent dataset"""
        responses.add(
            responses.GET,
            "https://data.public.lu/api/1/datasets/nonexistent-dataset/",
            json={"error": "Not found"},
            status=404
        )

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["--dataset", "nonexistent-dataset"])

            # Should complete but with error message
            assert result.exit_code == 0
            # The downloader handles this gracefully by printing an error
