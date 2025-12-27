"""CLI interface for udata-dl"""

import sys
from pathlib import Path

import click
from rich.console import Console

from .downloader import UdataDownloader


def build_api_url(domain: str) -> str:
    """
    Build the full API URL from a domain.

    Args:
        domain: Domain or full API URL

    Returns:
        Full API URL
    """
    domain = domain.rstrip('/')

    # If already a full URL with /api/, return as-is
    if '/api/' in domain:
        return domain

    # If it's just a domain, add https and /api/1
    if not domain.startswith('http'):
        domain = f"https://{domain}"

    # Add /api/1 if not present
    if not domain.endswith('/api/1'):
        domain = f"{domain}/api/1"

    return domain


@click.command()
@click.argument('organization', type=str, required=False)
@click.option(
    '--output', '-o',
    type=click.Path(),
    default='.',
    help='Output directory for downloaded files (default: .)'
)
@click.option(
    '--api-url', '-u',
    type=str,
    default='https://data.public.lu/api/1',
    help='Base URL of the udata API (default: https://data.public.lu/api/1)'
)
@click.option(
    '--dataset', '-d',
    type=str,
    help='Download only a specific dataset (by ID or slug)'
)
@click.option(
    '--force', '-f',
    is_flag=True,
    help='Force download even if files already exist'
)
@click.option(
    '--dry-run', '-n',
    is_flag=True,
    help='Show what would be downloaded without actually downloading'
)
@click.version_option()
def main(organization: str, output: str, api_url: str, dataset: str, force: bool, dry_run: bool):
    """
    Download and sync files from a udata platform for a given organization or dataset.

    ORGANIZATION is the identifier (ID or slug) of the organization (optional if --dataset is used).

    Examples:

      \b
      # Download all files from an organization
      udata-dl societe-nationale-des-chemins-de-fer-luxembourgeois

      \b
      # Download only one specific dataset
      udata-dl --dataset daily-meteorological-parameters-luxembourg-findel-airport-wmo-id-06590

      \b
      # Use a different udata instance
      udata-dl my-organization --api-url https://data.other-instance.org/api/1

      \b
      # Use just the domain (will add https and /api/1)
      udata-dl my-organization -u data.other-instance.org

      \b
      # Specify custom output directory
      udata-dl societe-nationale-des-chemins-de-fer-luxembourgeois -o /path/to/data

      \b
      # Force re-download of existing files
      udata-dl societe-nationale-des-chemins-de-fer-luxembourgeois --force

      \b
      # Dry run to see what would be downloaded
      udata-dl societe-nationale-des-chemins-de-fer-luxembourgeois --dry-run
    """
    console = Console()

    # Validate arguments - organization and dataset are mutually exclusive
    if not organization and not dataset:
        console.print("[bold red]Error:[/bold red] Either ORGANIZATION or --dataset must be specified")
        sys.exit(1)

    if organization and dataset:
        console.print("[bold red]Error:[/bold red] ORGANIZATION and --dataset are mutually exclusive. Use either one or the other.")
        sys.exit(1)

    # Build full API URL
    api_base_url = build_api_url(api_url)

    console.print(f"\n[bold cyan]udata-dl[/bold cyan] - udata platform downloader\n")
    console.print(f"[bold]API URL:[/bold] {api_base_url}")
    if organization:
        console.print(f"[bold]Organization:[/bold] {organization}")
    if dataset:
        console.print(f"[bold]Dataset:[/bold] {dataset}")
    console.print(f"[bold]Output directory:[/bold] {output}\n")

    try:
        downloader = UdataDownloader(
            output_dir=output,
            api_base_url=api_base_url,
            console=console
        )

        if dataset:
            # Download single dataset
            downloader.sync_dataset(
                dataset=dataset,
                force=force,
                dry_run=dry_run
            )
        else:
            # Download all datasets from organization
            downloader.sync_organization(
                organization=organization,
                force=force,
                dry_run=dry_run
            )

        console.print("\n[bold green]✓ Sync completed![/bold green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
