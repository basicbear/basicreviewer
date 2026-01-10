import click

from crev.init import init


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """crev - Code review, performance review, and CV tool."""
    pass


# Register subcommands
main.add_command(init)
