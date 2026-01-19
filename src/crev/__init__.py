import click

from crev.exim.export_cmd import export
from crev.exim.import_cmd import import_cmd
from crev.extract import extract
from crev.init import init
from crev.mcp_serv import mcp_serv
from crev.pull import pull
from crev.sum import sum


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """crev - Code review, performance review, and CV tool."""
    pass


# Register subcommands
main.add_command(init)
main.add_command(pull)
main.add_command(extract)
main.add_command(sum)
main.add_command(export)
main.add_command(import_cmd, name="import")
main.add_command(mcp_serv)
