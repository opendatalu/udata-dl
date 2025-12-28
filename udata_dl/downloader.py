"""Module for downloading and syncing files from udata platforms"""

import os
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn


class UdataDownloader:
    """Handles downloading and syncing files from udata platforms"""

    def __init__(
        self,
        output_dir: str = ".",
        api_base_url: str = "https://data.public.lu/api/1",
        console: Optional[Console] = None
    ):
        """
        Initialize downloader.

        Args:
            output_dir: Base directory for downloaded files
            api_base_url: Base URL for the udata API (default: data.public.lu)
            console: Rich console for output
        """
        self.output_dir = Path(output_dir)
        self.api_base_url = api_base_url.rstrip('/')  # Remove trailing slash
        self.console = console or Console()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'udata-dl/0.3.0'
        })

    def get_organization(self, organization: str) -> Optional[Dict]:
        """
        Get organization details including slug.

        Args:
            organization: Organization identifier (ID or slug)

        Returns:
            Organization dictionary or None on error
        """
        try:
            response = self.session.get(
                f"{self.api_base_url}/organizations/{organization}/",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.console.print(f"[red]Error fetching organization details: {e}[/red]")
            return None

    def get_dataset(self, dataset: str) -> Optional[Dict]:
        """
        Get a single dataset by ID or slug.

        Args:
            dataset: Dataset identifier (ID or slug)

        Returns:
            Dataset dictionary or None on error
        """
        try:
            response = self.session.get(
                f"{self.api_base_url}/datasets/{dataset}/",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.console.print(f"[red]Error fetching dataset: {e}[/red]")
            return None

    def get_datasets(self, organization: str) -> List[Dict]:
        """
        Get all datasets for an organization.

        Args:
            organization: Organization identifier

        Returns:
            List of dataset dictionaries
        """
        datasets = []
        page = 1

        self.console.print(f"[cyan]Fetching datasets for organization: {organization}[/cyan]")

        while True:
            try:
                response = self.session.get(
                    f"{self.api_base_url}/datasets/",
                    params={
                        "organization": organization,
                        "page": page,
                        "page_size": 100
                    }
                )
                response.raise_for_status()
                data = response.json()

                page_datasets = data.get("data", [])
                if not page_datasets:
                    break

                datasets.extend(page_datasets)
                self.console.print(f"[dim]  Found {len(datasets)} datasets so far...[/dim]")

                # Check if there are more pages
                if not data.get("next_page"):
                    break

                page += 1

            except requests.RequestException as e:
                self.console.print(f"[red]Error fetching datasets: {e}[/red]")
                break

        self.console.print(f"[green]Total datasets found: {len(datasets)}[/green]")
        return datasets

    def get_file_hash(self, filepath: Path, algorithm: str = "sha1") -> Optional[str]:
        """
        Calculate hash of a file.

        Args:
            filepath: Path to file
            algorithm: Hash algorithm (sha1, sha256, md5, etc.)

        Returns:
            Hash string or None if file doesn't exist
        """
        if not filepath.exists():
            return None

        # Map algorithm names to hashlib functions
        algorithm_map = {
            "sha1": hashlib.sha1,
            "sha2": hashlib.sha256,  # sha2 typically refers to sha256
            "sha256": hashlib.sha256,
            "md5": hashlib.md5,
        }

        hash_func = algorithm_map.get(algorithm.lower())
        if not hash_func:
            # Default to sha1 if algorithm not recognized
            hash_func = hashlib.sha1

        hasher = hash_func()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe filesystem use.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove or replace problematic characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename

    def download_file(
        self,
        url: str,
        filepath: Path,
        force: bool = False,
        checksum: Optional[Dict] = None
    ) -> Tuple[bool, str]:
        """
        Download a file with progress tracking.

        Args:
            url: URL to download
            filepath: Destination file path
            force: Force download even if file exists
            checksum: Optional dict with 'type' and 'value' for hash verification

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Check if file exists and verify with checksum if available
        if filepath.exists() and not force:
            # If checksum is provided, use it for comparison
            if checksum and checksum.get("value"):
                hash_type = checksum.get("type", "sha1")
                local_hash = self.get_file_hash(filepath, hash_type)
                remote_hash = checksum["value"].lower()

                if local_hash and local_hash.lower() == remote_hash:
                    return True, "skipped (checksum match)"

                # If hashes don't match, download
                return self._perform_download(url, filepath)

            # If no checksum, always re-download
            return self._perform_download(url, filepath)

        # Download the file
        return self._perform_download(url, filepath)

    def _perform_download(self, url: str, filepath: Path) -> Tuple[bool, str]:
        """
        Perform the actual file download.

        Args:
            url: URL to download
            filepath: Destination file path

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))

            # Create parent directories
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Download with progress
            with open(filepath, 'wb') as f:
                if total_size == 0:
                    f.write(response.content)
                else:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

            return True, "downloaded"

        except requests.RequestException as e:
            return False, f"error: {str(e)}"

    def sync_organization(self, organization: str, force: bool = False, dry_run: bool = False):
        """
        Sync all files from an organization.

        Args:
            organization: Organization identifier (ID or slug)
            force: Force download even if files exist
            dry_run: Only show what would be downloaded
        """
        # Get organization details to retrieve slug
        org_details = self.get_organization(organization)
        if not org_details:
            self.console.print("[red]Could not fetch organization details[/red]")
            return

        org_slug = org_details.get("slug")
        org_id = org_details.get("id")

        if not org_slug:
            self.console.print("[red]Organization slug not found in API response[/red]")
            return

        if not org_id:
            self.console.print("[red]Organization ID not found in API response[/red]")
            return

        org_name = org_details.get("name", organization)
        self.console.print(f"[bold]Organization:[/bold] {org_name}")
        self.console.print(f"[dim]Slug: {org_slug}[/dim]\n")

        # Use organization ID for datasets endpoint (it doesn't accept slugs)
        datasets = self.get_datasets(org_id)

        if not datasets:
            self.console.print("[yellow]No datasets found for this organization[/yellow]")
            return

        # Count total resources
        total_resources = 0
        for dataset in datasets:
            resources = [r for r in dataset.get("resources", []) if r.get("type") != "api"]
            total_resources += len(resources)
        self.console.print(f"[cyan]Total resources to process: {total_resources}[/cyan]\n")

        if dry_run:
            self.console.print("[yellow]DRY RUN MODE - No files will be downloaded[/yellow]\n")

        downloaded = 0
        skipped = 0
        errors = 0
        deleted = 0

        # Track expected files to identify orphaned local files
        expected_files = set()

        for dataset in datasets:
            dataset_slug = dataset.get("slug", "unknown")
            dataset_title = dataset.get("title", "Unknown Dataset")

            # exclude APIs
            resources = [r for r in dataset.get("resources", []) if r.get("type") != "api"]

            if not resources:
                continue

            self.console.print(f"\n[bold blue]Dataset:[/bold blue] {dataset_title}")
            self.console.print(f"[dim]  Slug: {dataset_slug}[/dim]")
            self.console.print(f"[dim]  Resources: {len(resources)}[/dim]")

            # Create dataset directory
            dataset_dir = self.output_dir / org_slug / dataset_slug

            for i, resource in enumerate(resources, 1):
                resource_url = resource.get("url")
                resource_title = resource.get("title", f"resource_{i}")
                resource_format = resource.get("format", "")
                resource_checksum = resource.get("checksum")

                if not resource_url:
                    self.console.print(f"  [yellow]⚠ Skipping resource {i}: No URL[/yellow]")
                    skipped += 1
                    continue

                # Extract filename from URL
                parsed_url = urlparse(resource_url)
                filename = os.path.basename(parsed_url.path) or f"resource_{i}"
                filename = self.sanitize_filename(filename)

                # Add extension if not present
                if resource_format and not filename.endswith(f".{resource_format.lower()}"):
                    filename = f"{filename}.{resource_format.lower()}"

                filepath = dataset_dir / filename

                # Track expected file
                expected_files.add(filepath)

                if dry_run:
                    checksum_info = ""
                    if resource_checksum and resource_checksum.get("value"):
                        hash_type = resource_checksum.get("type", "sha1")
                        checksum_info = f" [dim]({hash_type})[/dim]"
                    self.console.print(f"  [dim]Would download:[/dim] {filename}{checksum_info}")
                    continue

                # Download the file with checksum verification
                success, message = self.download_file(
                    resource_url,
                    filepath,
                    force,
                    checksum=resource_checksum
                )

                if success:
                    if "skipped" in message:
                        self.console.print(f"  [dim]⊘ {filename} - {message}[/dim]")
                        skipped += 1
                    else:
                        self.console.print(f"  [green]✓ {filename} - {message}[/green]")
                        downloaded += 1
                else:
                    self.console.print(f"  [red]✗ {filename} - {message}[/red]")
                    errors += 1

        # Delete files that no longer exist in the API
        if not dry_run:
            org_dir = self.output_dir / org_slug
            if org_dir.exists():
                self.console.print("\n[cyan]Checking for removed files...[/cyan]")

                # Find all files in the organization directory
                existing_files = set()
                for path in org_dir.rglob("*"):
                    if path.is_file():
                        existing_files.add(path)

                # Find orphaned files
                orphaned_files = existing_files - expected_files

                if orphaned_files:
                    self.console.print(f"[yellow]Found {len(orphaned_files)} file(s) no longer in API[/yellow]")
                    for orphaned_file in sorted(orphaned_files):
                        try:
                            orphaned_file.unlink()
                            relative_path = orphaned_file.relative_to(self.output_dir)
                            self.console.print(f"  [red]✗ Deleted: {relative_path}[/red]")
                            deleted += 1
                        except Exception as e:
                            self.console.print(f"  [red]Error deleting {orphaned_file.name}: {e}[/red]")

                    # Clean up empty directories
                    for dataset_dir in org_dir.iterdir():
                        if dataset_dir.is_dir() and not any(dataset_dir.iterdir()):
                            try:
                                dataset_dir.rmdir()
                                self.console.print(f"  [dim]Removed empty directory: {dataset_dir.name}[/dim]")
                            except:
                                pass
                else:
                    self.console.print("[dim]No orphaned files found[/dim]")

        # Print summary
        self.console.print("\n[bold]Summary:[/bold]")
        self.console.print(f"  [green]Downloaded: {downloaded}[/green]")
        self.console.print(f"  [dim]Skipped: {skipped}[/dim]")
        if deleted > 0:
            self.console.print(f"  [red]Deleted: {deleted}[/red]")
        if errors > 0:
            self.console.print(f"  [red]Errors: {errors}[/red]")

    def sync_dataset(
        self,
        dataset: str,
        force: bool = False,
        dry_run: bool = False
    ):
        """
        Sync files from a single dataset.

        Args:
            dataset: Dataset identifier (ID or slug)
            force: Force download even if files exist
            dry_run: Only show what would be downloaded
        """
        # Fetch the dataset
        dataset_data = self.get_dataset(dataset)
        if not dataset_data:
            self.console.print("[red]Could not fetch dataset details[/red]")
            return

        dataset_slug = dataset_data.get("slug", "unknown")
        dataset_title = dataset_data.get("title", "Unknown Dataset")

        # exclude APIs
        resources = [r for r in dataset_data.get("resources", []) if r.get("type") != "api"]

        # Extract organization from dataset
        org_data = dataset_data.get("organization")
        if not org_data:
            owner_data = dataset_data.get("owner")
            if owner_data:
                org_slug = owner_data.get("slug", "")
                org_name = owner_data.get("first_name", "")+" "+owner_data.get("last_name", "")
            else:
                org_slug = ""
                org_name = "Unknown"
        else:
            org_slug = org_data.get("slug")
            org_name = org_data.get("name", org_slug)



        self.console.print(f"[bold]Organization:[/bold] {org_name}")
        self.console.print(f"[dim]Slug: {org_slug}[/dim]")
        self.console.print(f"[bold blue]Dataset:[/bold blue] {dataset_title}")
        self.console.print(f"[dim]Slug: {dataset_slug}[/dim]")
        self.console.print(f"[dim]Resources: {len(resources)}[/dim]\n")

        if not resources:
            self.console.print("[yellow]No resources found for this dataset[/yellow]")
            return

        if dry_run:
            self.console.print("[yellow]DRY RUN MODE - No files will be downloaded[/yellow]\n")

        downloaded = 0
        skipped = 0
        errors = 0
        deleted = 0

        # Track expected files to identify orphaned local files
        expected_files = set()

        # Create dataset directory
        dataset_dir = self.output_dir / org_slug / dataset_slug

        for i, resource in enumerate(resources, 1):
            resource_url = resource.get("url")
            resource_title = resource.get("title", f"resource_{i}")
            resource_format = resource.get("format", "")
            resource_checksum = resource.get("checksum")

            if not resource_url:
                self.console.print(f"  [yellow]⚠ Skipping resource {i}: No URL[/yellow]")
                skipped += 1
                continue

            # Extract filename from URL
            parsed_url = urlparse(resource_url)
            filename = os.path.basename(parsed_url.path) or f"resource_{i}"
            filename = self.sanitize_filename(filename)

            # Add extension if not present
            if resource_format and not filename.endswith(f".{resource_format.lower()}"):
                filename = f"{filename}.{resource_format.lower()}"

            filepath = dataset_dir / filename

            # Track expected file
            expected_files.add(filepath)

            if dry_run:
                checksum_info = ""
                if resource_checksum and resource_checksum.get("value"):
                    hash_type = resource_checksum.get("type", "sha1")
                    checksum_info = f" [dim]({hash_type})[/dim]"
                self.console.print(f"  [dim]Would download:[/dim] {filename}{checksum_info}")
                continue

            # Download the file with checksum verification
            success, message = self.download_file(
                resource_url,
                filepath,
                force,
                checksum=resource_checksum
            )

            if success:
                if "skipped" in message:
                    self.console.print(f"  [dim]⊘ {filename} - {message}[/dim]")
                    skipped += 1
                else:
                    self.console.print(f"  [green]✓ {filename} - {message}[/green]")
                    downloaded += 1
            else:
                self.console.print(f"  [red]✗ {filename} - {message}[/red]")
                errors += 1

        # Delete files that no longer exist in the dataset
        if not dry_run and dataset_dir.exists():
            self.console.print("\n[cyan]Checking for removed files...[/cyan]")

            # Find all files in the dataset directory
            existing_files = set()
            for path in dataset_dir.rglob("*"):
                if path.is_file():
                    existing_files.add(path)

            # Find orphaned files
            orphaned_files = existing_files - expected_files

            if orphaned_files:
                self.console.print(f"[yellow]Found {len(orphaned_files)} file(s) no longer in dataset[/yellow]")
                for orphaned_file in sorted(orphaned_files):
                    try:
                        orphaned_file.unlink()
                        relative_path = orphaned_file.relative_to(self.output_dir)
                        self.console.print(f"  [red]✗ Deleted: {relative_path}[/red]")
                        deleted += 1
                    except Exception as e:
                        self.console.print(f"  [red]Error deleting {orphaned_file.name}: {e}[/red]")

                # Clean up empty directory if needed
                if dataset_dir.exists() and not any(dataset_dir.iterdir()):
                    try:
                        dataset_dir.rmdir()
                        self.console.print(f"  [dim]Removed empty directory: {dataset_dir.name}[/dim]")
                    except:
                        pass
            else:
                self.console.print("[dim]No orphaned files found[/dim]")

        # Print summary
        self.console.print("\n[bold]Summary:[/bold]")
        self.console.print(f"  [green]Downloaded: {downloaded}[/green]")
        self.console.print(f"  [dim]Skipped: {skipped}[/dim]")
        if deleted > 0:
            self.console.print(f"  [red]Deleted: {deleted}[/red]")
        if errors > 0:
            self.console.print(f"  [red]Errors: {errors}[/red]")


# Backward compatibility alias
DataPublicLuDownloader = UdataDownloader
