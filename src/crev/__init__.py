import click

from crev.extract import extract
from crev.init import init
from crev.pull import pull


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """crev - Code review, performance review, and CV tool."""
    pass


# Register subcommands
main.add_command(init)
main.add_command(pull)
main.add_command(extract)
