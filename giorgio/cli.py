import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from importlib.metadata import entry_points

import typer

from .execution_engine import ExecutionEngine
from .project_manager import initialize_project, create_script


# Initialize the CLI application
app = typer.Typer(help="Giorgio automation framework CLI")


def _parse_params(param_list: List[str]) -> Dict[str, Any]:
    """
    Parses a list of parameter strings in the format 'key=value' into a dictionary.

    :param param_list: List of parameter strings to parse.
    :type param_list: List[str]
    :returns: Dictionary mapping keys to their corresponding values.
    :rtype: Dict[str, Any]
    :raises typer.BadParameter: If any entry does not contain an '=' character.
    """

    params: Dict[str, Any] = {}
    
    for entry in param_list:
        if "=" not in entry:
            raise typer.BadParameter(f"Invalid parameter format: '{entry}', expected key=value")
        
        key, raw = entry.split("=", 1)
        params[key] = raw
    
    return params


def _discover_ui_renderers() -> Dict[str, type]:
    """
    Discover all registered UIRenderer plugins under the
    'giorgio.ui_renderers' entry point group.
    Returns a mapping {name: RendererClass}.

    :returns: Dictionary mapping renderer names to their classes.
    :rtype: Dict[str, type]
    """
    
    try:
        # Python 3.10+ API
        eps = entry_points(group="giorgio.ui_renderers")
    
    except TypeError:
        # Older API returns a dict-like
        eps_all = entry_points()
        eps = eps_all.get("giorgio.ui_renderers", [])
    
    renderers: Dict[str, type] = {}
    
    for ep in eps:
        try:
            renderers[ep.name] = ep.load()
        
        except Exception as e:
            print(f"Warning: could not load UI plugin {ep.name!r}: {e}")
    
    return renderers


@app.command()
def init(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Directory to initialize as a Giorgio project")
):
    """
    Initialize a new Giorgio project.

    Creates the following structure under the specified directory:
      - scripts/          (directory for user scripts)
      - modules/          (directory for shared modules, with __init__.py)
      - .env              (blank environment file)
      - .giorgio/         (configuration directory)
          - config.json   (project configuration)

    If no directory is specified, initializes in the current directory.

    :param name: Optional directory name to initialize as a Giorgio project. Defaults to current directory.
    :type name: Optional[str]
    :returns: None
    :rtype: None
    :raises FileExistsError: If critical directories or files already exist.
    """
    
    project_root = Path(name or ".").resolve()
    
    try:
        initialize_project(project_root)
        typer.echo(f"Initialized Giorgio project at {project_root}")
    
    except Exception as e:
        typer.echo(f"Error initializing project: {e}")
        sys.exit(1)


@app.command()
def new(
    script: str = typer.Argument(..., help="Name of the new script to scaffold")
):
    """
    Scaffold a new automation script under scripts/<script>.

    Creates a new directory under scripts/ with the specified name,
    containing a basic script template.

    :param script: Name of the new script folder to create under scripts/.
    :type script: str
    :returns: None
    :rtype: None
    :raises FileExistsError: If the script directory already exists.
    """
    
    project_root = Path(".").resolve()
    
    try:
        create_script(project_root, script)
        typer.echo(f"Created new script '{script}'")
    
    except Exception as e:
        typer.echo(f"Error creating script: {e}")
        sys.exit(1)


@app.command()
def run(
    script: str = typer.Argument(..., help="Name of the script folder under scripts/"),
    param: List[str] = typer.Option(
        None,
        "--param",
        "-p",
        help="Parameter assignment in the form key=value. Repeat for multiple params.",
    ),
):
    """
    Execute a script in non-interactive mode. All parameters must be provided
    via --param.

    The script must be located under scripts/**/script.py.

    :param script: Name of the script folder under scripts/ to execute.
    :type script: str
    :param param: List of parameters in the form key=value to pass to the script.
    :type param: List[str]
    format.
    :returns: None
    :rtype: None
    :raises typer.BadParameter: If any parameter does not contain an '='
    character.
    :raises Exception: If the script execution fails for any reason.
    """
    
    project_root = Path(".").resolve()
    engine = ExecutionEngine(project_root)
    cli_args = _parse_params(param or [])
    
    try:
        engine.run_script(script, cli_args=cli_args)
    
    except Exception as e:
        typer.echo(f"Error: {e}")
        sys.exit(1)


@app.command()
def start(
    ui_name: str = typer.Option(
        None,
        "--ui",
        "-u",
        help="UI renderer to use for interactive mode",
        show_default=True
    )
):
    """
    Launch interactive mode: select a script and enter parameters via prompts.

    This command lists all scripts found under scripts/**/script.py and allows
    the user to select one. It then prompts for any required parameters before
    executing the script.

    If no scripts are found, it exits with an error message.
    
    If the user interrupts the execution, it exits gracefully.
    
    If an error occurs during script execution, it prints the error message and
    exits with a non-zero status.

    :param ui_name: Name of the UI renderer to use for interactive mode.
    :type ui_name: str
    :returns: None
    :rtype: None
    :raises typer.BadParameter: If the specified UI renderer is not available.
    :raises Exception: If the script execution fails for any reason.
    """

    project_root = Path(".").resolve()
    engine = ExecutionEngine(project_root)
    renderers = _discover_ui_renderers()

    # Check if any UI renderers are available
    if not renderers:
        typer.echo("No UI renderers available.", err=True)
        raise typer.Exit(code=1)

    # If no specific UI renderer is provided, use the first available one
    if ui_name is None:
        ui_name = next(iter(renderers))

    # Check if the specified UI renderer exists
    if ui_name not in renderers:
        typer.echo(
            f"Unknown UI renderer: {ui_name}. Available: {', '.join(renderers)}",
            err=True
        )
        raise typer.Exit(code=1)

    # Instantiate the selected renderer
    renderer_cls = renderers[ui_name]
    renderer = renderer_cls()

    # List all scripts in scripts/ directory
    scripts_dir = project_root / "scripts"
    scripts = [
        p.relative_to(scripts_dir).parent.as_posix()
        for p in sorted(scripts_dir.rglob("script.py"))
    ]

    if not scripts:
        typer.echo("No scripts found in scripts/ directory.")
        sys.exit(1)

    # Use the renderer to list scripts and prompt for selection
    script = renderer.list_scripts(scripts)
    
    if not script:
        typer.echo("No script selected.")
        sys.exit(0)

    # Run the selected script with parameters
    try:
        engine.run_script(
            script,
            cli_args=None,
            add_params_callback=lambda s, e: renderer.prompt_params(s, e),
        )
    
    except KeyboardInterrupt:
        typer.echo("\nExecution interrupted by user.")
        sys.exit(1)
    
    except Exception as e:
        typer.echo(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    app()
