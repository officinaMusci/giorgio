import json
import sys
import logging
from pathlib import Path
from importlib.metadata import version as _get_version, PackageNotFoundError
import questionary
from types import MappingProxyType
from typing import Optional, Tuple

from .validation import validate_project, summarize_validation


logger = logging.getLogger("giorgio.project_manager")


def initialize_project(root: Path, project_name: str = None) -> None:
    """
    Initialize a Giorgio project at the given root path.

    Creates the following structure under root:
      - scripts/          (directory for user scripts)
      - modules/          (directory for shared modules, with __init__.py)
      - .env              (blank environment file)
      - .giorgio/         (configuration directory)
          - config.json   (project configuration)

    :param root: The root directory where the project will be initialized.
    :type root: Path
    :param project_name: Optional name for the project to be stored in
    config.json.
    :type project_name: str, optional
    :raises FileExistsError: If any of the required directories or files already
    exist.    
    """

    logger.info("Initializing Giorgio project at %s", root)

    # Check/create the root directory
    root.mkdir(parents=True, exist_ok=True)

    # Create scripts/ (for user scripts)
    scripts_dir = root / "scripts"
    if scripts_dir.exists():
        logger.error("Cannot initialize project: directory '%s' already exists", scripts_dir)
        raise FileExistsError(f"Directory '{scripts_dir}' already exists.")
    
    scripts_dir.mkdir()
    logger.debug("Created scripts directory at %s", scripts_dir)

    # Create modules/ (for shared modules) + __init__.py
    modules_dir = root / "modules"
    if modules_dir.exists():
        logger.error("Cannot initialize project: directory '%s' already exists", modules_dir)
        raise FileExistsError(f"Directory '{modules_dir}' already exists.")
    
    modules_dir.mkdir()
    logger.debug("Created modules directory at %s", modules_dir)
    
    # Create __init__.py inside to make 'modules' importable
    init_file = modules_dir / "__init__.py"
    init_file.touch()
    logger.debug("Created modules __init__ at %s", init_file)

    # Create .env (empty file)
    env_file = root / ".env"
    if env_file.exists():
        logger.error("Cannot initialize project: file '%s' already exists", env_file)
        raise FileExistsError(f"File '{env_file}' already exists.")
    
    env_file.touch()
    logger.debug("Created .env file at %s", env_file)

    # Create requirements.txt with default dependency
    requirements_file = root / "requirements.txt"
    if requirements_file.exists():
        logger.error("Cannot initialize project: file '%s' already exists", requirements_file)
        raise FileExistsError(f"File '{requirements_file}' already exists.")

    requirements_file.write_text("giorgio\n", encoding="utf-8")
    logger.debug("Created requirements.txt at %s", requirements_file)

    # Create .giorgio/ and config.json
    giorgio_dir = root / ".giorgio"
    if giorgio_dir.exists():
        logger.error("Cannot initialize project: directory '%s' already exists", giorgio_dir)
        raise FileExistsError(f"Directory '{giorgio_dir}' already exists.")
    
    giorgio_dir.mkdir()
    logger.debug("Created .giorgio directory at %s", giorgio_dir)

    config_file = giorgio_dir / "config.json"
    
    try:
        current_version = _get_version("giorgio")
    
    except PackageNotFoundError:
        current_version = "0.0.0"

    default_config = {
        "giorgio_version": current_version,
        "module_paths": ["modules"],
        "logging": {"level": "warning"}
    }
    
    if project_name:
        default_config["project_name"] = project_name

    with config_file.open("w", encoding="utf-8") as f:
        json.dump(default_config, f, indent=2)
    logger.info("Project initialized at %s", root)


def create_script(project_root: Path, script: str, template: str = None):
    """
    Creates a new script directory and script.py file under scripts/.

    :param project_root: Project root path.
    :type project_root: Path
    :param script: Script name (directory under scripts/).
    :type script: str
    :param template: Optional script.py content to use instead of the default template.
    :type template: Optional[str]
    :raises FileExistsError: If the script directory already exists.
    :raises FileNotFoundError: If the scripts directory does not exist.
    """
    logger.info("Creating script '%s' under project %s", script, project_root)

    scripts_dir = project_root / "scripts"
    if not scripts_dir.exists():
        logger.error("Cannot create script '%s': scripts directory '%s' missing", script, scripts_dir)
        raise FileNotFoundError(f"Scripts directory '{scripts_dir}' does not exist.")

    script_dir = scripts_dir / script
    if script_dir.exists():
        logger.error("Cannot create script '%s': directory '%s' already exists", script, script_dir)
        raise FileExistsError(f"Script directory '{script_dir}' already exists.")

    # Create all parent directories and __init__.py at each level
    parts = script_dir.relative_to(scripts_dir).parts
    current = scripts_dir
    for part in parts:
        current = current / part
        current.mkdir(exist_ok=True)
        init_file = current / "__init__.py"
        if not init_file.exists():
            init_file.touch()
            logger.debug("Created package init at %s", init_file)

    # Determine content
    if template is not None:
        # Replace __SCRIPT_PATH__ in provided template
        script_path_str = script.replace("\\", "/")
        content = template.replace("__SCRIPT_PATH__", script_path_str)
        logger.debug("Using custom template for script '%s'", script)
    else:
        # load built-in template file if available
        base_dir = Path(__file__).parent
        tpl_file = base_dir / "templates" / "script_template.py"
        if tpl_file.exists():
            raw = tpl_file.read_text(encoding="utf-8")
            script_path_str = script.replace("\\", "/")
            content = raw.replace("__SCRIPT_PATH__", script_path_str)
            logger.debug("Loaded built-in template from %s", tpl_file)
        else:
            # fallback to default inline template
            content = '''from giorgio.execution_engine import Context, GiorgioCancellationError

CONFIG = {
    "name": "",
    "description": ""
}

PARAMS = {}

def run(context: Context):
    try:
        # Your script logic here
        pass
    except GiorgioCancellationError:
        print("Execution was cancelled by the user.")
'''

    # Write out the script file
    script_file = script_dir / "script.py"
    script_file.write_text(content, encoding="utf-8")
    logger.info("Script '%s' created at %s", script, script_file)


def upgrade_project(root: Path, force: bool = False) -> None:
    """
    Perform a project upgrade to the latest Giorgio version.

    - Reads the .giorgio/config.json file to get the current project version.
    - Compares it to the installed version of Giorgio.
    - If force=True: directly writes the new version to config.json.
    - Otherwise: performs a validation (dry-run) of all scripts under 'scripts/'.
      Each script is imported and it is checked that CONFIG contains 'name' and 'description'.
      If validation succeeds, the user is prompted to confirm the update, then the file is modified.
      
    :param root: Path to the project root.
    :type root: Path
    :param force: If True, skips validation and directly updates the version.
    :type force: bool
    :raises FileNotFoundError: If the configuration file or scripts directory does not exist.
    :raises PackageNotFoundError: If Giorgio is not installed.
    """
    
    logger.info("Upgrading Giorgio project at %s (force=%s)", root, force)

    giorgio_dir = root / ".giorgio"
    config_file = giorgio_dir / "config.json"
    scripts_dir = root / "scripts"

    if not config_file.exists():
        logger.error("Cannot upgrade: configuration file '%s' not found", config_file)
        raise FileNotFoundError(f"Configuration file '{config_file}' not found.")
    
    if not scripts_dir.exists():
        logger.error("Cannot upgrade: scripts directory '%s' not found", scripts_dir)
        raise FileNotFoundError(f"Scripts directory '{scripts_dir}' not found.")

    # Load the project version from config.json
    with config_file.open("r", encoding="utf-8") as f:
        config_data = json.load(f)
    
    project_version = config_data.get("giorgio_version", "0.0.0")

    # Get the installed version
    try:
        installed_version = _get_version("giorgio")
    
    except PackageNotFoundError:
        installed_version = "0.0.0"

    logger.info(
        "Project version %s; installed version %s", project_version, installed_version
    )
    print(f"Current project version: {project_version}")
    print(f"Installed Giorgio version: {installed_version}")

    if project_version == installed_version and not force:
        print("Project is already up-to-date.")
        logger.info("Project at %s already up-to-date", root)
        return

    def validate_scripts() -> bool:
        """Validate scripts using static analysis without executing them."""

        logger.debug("Validating scripts under %s", scripts_dir)
        results = validate_project(root)
        summary = summarize_validation(results)

        if summary.no_scripts:
            logger.debug("No scripts found for validation in %s", scripts_dir)
            print("No scripts found in scripts/ directory.")
            return True

        for rel_path, messages in summary.entries:
            print(f"- {rel_path}")

            for message in messages:
                prefix = "ERROR" if message.level == "error" else "WARN"
                print(f"    [{prefix}] {message.message}")

        if summary.has_errors:
            logger.error("Validation failed due to script errors.")
            print("Validation failed. Please address the errors above and retry.")
            return False

        if summary.has_warnings:
            logger.warning("Validation completed with warnings.")
            print("Validation completed with warnings. Proceed with caution.")
            return True

        logger.info("Validation completed successfully for all scripts.")
        print("Validation completed successfully.")

        return True

    if force:
        confirm = True
    
    else:
        logger.info("Running validation prior to upgrade for project at %s", root)
        print("Running validation on all scripts...")
        
        if not validate_scripts():
            logger.error("Validation failed; aborting upgrade for project at %s", root)
            raise RuntimeError("Upgrade aborted due to validation failures.")
        
        # User confirmation
        confirm = questionary.confirm("All scripts validated successfully. Update project version?").ask()
        logger.debug("User confirmation for upgrade: %s", confirm)

    if confirm:
        config_data["giorgio_version"] = installed_version
        
        with config_file.open("w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
        
        logger.info("Project at %s upgraded to version %s", root, installed_version)
        print(f"Project upgraded to Giorgio version {installed_version}.")
    
    else:
        logger.info("Project upgrade canceled for %s", root)
        print("Upgrade canceled.")


def get_project_config(project_root: Path):
    """
    Loads the Giorgio project config.json as a read-only MappingProxyType.

    :param project_root: Path to the project root directory.
    :type project_root: Path
    :returns: Read-only config dictionary.
    :rtype: MappingProxyType
    :raises FileNotFoundError: If config.json does not exist.
    :raises json.JSONDecodeError: If config.json is invalid.
    """
    config_path = project_root / ".giorgio" / "config.json"
    logger.debug("Loading project configuration from %s", config_path)
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    logger.debug("Configuration keys loaded: %s", list(config))
    return MappingProxyType(config)


def get_version_status(project_root: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Retrieve the configured Giorgio version for a project and the installed version.

    :param project_root: Path to the project root directory.
    :type project_root: Path
    :returns: A tuple of (configured_version, installed_version). Either value may be None.
    :rtype: Tuple[Optional[str], Optional[str]]
    :raises FileNotFoundError: If config.json does not exist.
    :raises json.JSONDecodeError: If config.json is invalid JSON.
    """

    config = get_project_config(project_root)
    configured_version = config.get("giorgio_version")

    try:
        installed_version = _get_version("giorgio")

    except PackageNotFoundError:
        installed_version = None

    return configured_version, installed_version
