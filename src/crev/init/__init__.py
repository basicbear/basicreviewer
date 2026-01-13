"""Init command for crev CLI."""

import json
from pathlib import Path

import click


@click.command()
@click.argument("path", type=click.Path())
def init(path: str) -> None:
    """Initialize a new crev project.

    Creates a folder at PATH with a configs.json configuration file and a sample .env file.
    """
    project_path = Path(path)

    # Create the directory
    try:
        project_path.mkdir(parents=True, exist_ok=False)
        click.echo(f"Created directory: {project_path.absolute()}")
    except FileExistsError:
        click.echo(f"Error: Directory '{path}' already exists", err=True)
        raise click.Abort()

    # Load configs template from assets
    template_file = Path(__file__).parent / "assets" / "configs_template.json"
    with template_file.open("r") as f:
        configs_config = json.load(f)

    # Write configs.json to project directory
    configs_file = project_path / "configs.json"
    with configs_file.open("w") as f:
        json.dump(configs_config, f, indent=2)

    # Load .env template from assets
    env_template_file = Path(__file__).parent / "assets" / ".env.template"
    with env_template_file.open("r") as f:
        env_content = f.read()

    # Write .env file to project directory
    env_file = project_path / ".env"
    with env_file.open("w") as f:
        f.write(env_content)

    # Read success message from file
    msg_file = Path(__file__).parent / "assets" / "init_success.txt"
    with msg_file.open("r") as f:
        message = f.read().format(
            project_path=project_path.absolute(), configs_file=configs_file
        )
    click.echo(message)
