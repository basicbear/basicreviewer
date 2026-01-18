"""Export and Import commands for crev workspace files."""

import click

from crev.exim.export_cmd import export
from crev.exim.import_cmd import import_cmd


@click.group()
def exim() -> None:
    """Export and import crev workspace files."""
    pass


exim.add_command(export)
exim.add_command(import_cmd, name="import")
