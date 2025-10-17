import logging
import sys
from json import JSONDecodeError
from pathlib import Path
from typing import List, Dict, Any, Optional
from importlib.metadata import entry_points

import typer

from .logconfig import configure_logging

from .execution_engine import ExecutionEngine
from .project_manager import (
    initialize_project,
    create_script,
    upgrade_project,
    get_version_status,
)
from .validation import validate_project, summarize_validation
from .ai_client import AIScriptingClient


# Initialize the CLI application
project_root = Path(".").resolve()
# Configure logging early so Typer/Click honor the project's logging level
configure_logging(project_root=project_root)

app = typer.Typer(help="Giorgio automation framework CLI")
logger = logging.getLogger("giorgio.cli")


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

        except Exception as exc:
            logger.warning("Could not load UI plugin %s: %s", ep.name, exc, exc_info=True)
            typer.echo(f"Warning: could not load UI plugin {ep.name!r}: {exc}")
    
    return renderers


def _warn_if_version_mismatch(project_root: Path) -> None:
    try:
        configured_version, installed_version = get_version_status(project_root)

    except FileNotFoundError:
        logger.debug("No Giorgio configuration found at %s; skipping version check", project_root)
        return

    except JSONDecodeError as exc:
        logger.warning("Invalid Giorgio configuration at %s: %s", project_root, exc, exc_info=True)
        return

    if not configured_version or not installed_version:
        logger.debug(
            "Skipping version warning due to missing values (configured=%s, installed=%s)",
            configured_version,
            installed_version,
        )
        return

    if configured_version == installed_version:
        logger.debug("Project version %s matches installed Giorgio", configured_version)
        return

    warning = (
        f"⚠️  Project expects Giorgio {configured_version}, but version {installed_version} is installed."
    )
    hint = "Run `giorgio upgrade` to update the project configuration."
    logger.warning("%s %s", warning, hint)
    typer.secho(warning, fg="yellow")
    typer.secho(hint, fg="yellow")


@app.command()
def init(
    name: Optional[str] = typer.Argument(
        None,
        help="Directory to initialize as a Giorgio project"
    )
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
    logger.info("Initializing Giorgio project at %s", project_root)

    try:
        initialize_project(project_root)
        logger.info("Successfully initialized project at %s", project_root)
        typer.echo(f"Initialized Giorgio project at {project_root}")

    except Exception as exc:
        logger.exception("Failed to initialize project at %s", project_root)
        typer.echo(f"Error initializing project: {exc}")
        sys.exit(1)


@app.command()
def new(
    script: str = typer.Argument(..., help="Name of the new script to scaffold"),
    ai_prompt: Optional[str] = typer.Option(
        None,
        "--ai-prompt",
        help="Instructions for AI to generate the script (requires AI config in .giorgio/config.json)",
    ),
):
    """
    Scaffold a new automation script under scripts/<script>.

    If --ai is provided, uses an OpenAI-compatible API to generate the script
    based on the given instructions and the AI configuration in config.json.

    :param script: Name of the new script folder to create under scripts/.
    :type script: str
    :param ai: Optional instructions for AI to generate the script.
    :type ai: Optional[str]
    :returns: None
    :rtype: None
    :raises FileExistsError: If the script directory already exists.
    """
    project_root = Path(".").resolve()
    _warn_if_version_mismatch(project_root)
    logger.info("Scaffolding new script '%s' (AI prompt provided: %s)", script, bool(ai_prompt))

    try:
        if ai_prompt:
            client = AIScriptingClient(project_root)
            script_content = client.generate_script(ai_prompt)

            create_script(project_root, script, template=script_content)
            logger.debug("Generated script content via AI for '%s'", script)

        else:
            create_script(project_root, script)

        logger.info("Script '%s' created successfully", script)
        typer.echo(f"Created new script '{script}'")

    except Exception as exc:
        logger.exception("Failed to create script '%s'", script)
        typer.echo(f"Error creating script: {exc}")
        sys.exit(1)


@app.command()
def upgrade(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip script validation and update the project to the installed Giorgio version.",
    )
):
    """
    Update the project's pinned Giorgio version in .giorgio/config.json.

    When run without --force, all scripts are validated before the version is updated.
    With --force, validation is skipped and the version is updated immediately.
    """

    project_root = Path(".").resolve()
    logger.info("Running upgrade command for project at %s (force=%s)", project_root, force)

    try:
        upgrade_project(project_root, force=force)

    except Exception as exc:
        logger.exception("Failed to upgrade project at %s", project_root)
        typer.echo(f"Error upgrading project: {exc}")
        sys.exit(1)


@app.command()
def validate():
    """Validate all Giorgio scripts without running them."""

    project_root = Path(".").resolve()
    _warn_if_version_mismatch(project_root)

    results = validate_project(project_root)
    summary = summarize_validation(results)

    if summary.no_scripts:
        typer.echo("No scripts found in scripts/ directory.")
        raise typer.Exit(code=0)

    for rel_path, messages in summary.entries:
        typer.echo(f"- {rel_path}")

        for message in messages:
            fg = "red" if message.level == "error" else "yellow"
            typer.secho(f"    [{message.level.upper()}] {message.message}", fg=fg)

    if summary.has_errors:
        typer.secho("Validation failed. Please address the errors above and retry.", fg="red")
        raise typer.Exit(code=1)

    if summary.has_warnings:
        typer.secho("Validation completed with warnings. Proceed with caution.", fg="yellow")
    else:
        typer.secho("All scripts validated successfully.", fg="green")


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
    _warn_if_version_mismatch(project_root)
    engine = ExecutionEngine(project_root)
    cli_args = _parse_params(param or [])
    logger.info("Running script '%s' with CLI params: %s", script, list(cli_args.keys()))

    try:
        engine.run_script(script, cli_args=cli_args)
        logger.info("Script '%s' completed", script)

    except KeyboardInterrupt:
        logger.warning("Script '%s' interrupted by user", script)
        typer.echo("\nExecution interrupted by user.")
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
    _warn_if_version_mismatch(project_root)
    engine = ExecutionEngine(project_root)
    renderers = _discover_ui_renderers()
    logger.debug("Discovered UI renderers: %s", list(renderers))

    # Check if any UI renderers are available
    if not renderers:
        logger.error("No UI renderers available")
        typer.echo("No UI renderers available.", err=True)
        raise typer.Exit(code=1)

    # If no specific UI renderer is provided, use the first available one
    if ui_name is None:
        ui_name = next(iter(renderers))

    # Check if the specified UI renderer exists
    if ui_name not in renderers:
        available = ", ".join(renderers)
        logger.error("Unknown UI renderer %s. Available: %s", ui_name, available)
        typer.echo(
            f"Unknown UI renderer: {ui_name}. Available: {available}.",
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
    logger.debug("Found %d scripts for interactive mode", len(scripts))

    if not scripts:
        logger.error("No scripts found in scripts/ directory")
        typer.echo("No scripts found in scripts/ directory.")
        sys.exit(1)

    # Use the renderer to list scripts and prompt for selection
    script = renderer.list_scripts(scripts)

    if not script:
        logger.info("No script selected in interactive mode")
        typer.echo("No script selected.")
        sys.exit(0)

    # Run the selected script with parameters
    try:
        logger.info("Starting interactive execution for script '%s'", script)
        engine.run_script(
            script,
            cli_args=None,
            add_params_callback=lambda s, e: renderer.prompt_params(s, e),
        )
        logger.info("Interactive execution for script '%s' completed", script)

    except KeyboardInterrupt:
        logger.warning("Interactive execution for script '%s' interrupted by user", script)
        typer.echo("\nExecution interrupted by user.")
        sys.exit(1)


if __name__ == "__main__":
    app()
