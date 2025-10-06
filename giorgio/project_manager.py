import json
import sys
from pathlib import Path
from importlib.metadata import version as _get_version, PackageNotFoundError
import questionary
import importlib.util
from types import MappingProxyType


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

    # Check/create the root directory
    root.mkdir(parents=True, exist_ok=True)

    # Create scripts/ (for user scripts)
    scripts_dir = root / "scripts"
    if scripts_dir.exists():
        raise FileExistsError(f"Directory '{scripts_dir}' already exists.")
    
    scripts_dir.mkdir()

    # Create modules/ (for shared modules) + __init__.py
    modules_dir = root / "modules"
    if modules_dir.exists():
        raise FileExistsError(f"Directory '{modules_dir}' already exists.")
    
    modules_dir.mkdir()
    
    # Create __init__.py inside to make 'modules' importable
    init_file = modules_dir / "__init__.py"
    init_file.touch()

    # Create .env (empty file)
    env_file = root / ".env"
    if env_file.exists():
        raise FileExistsError(f"File '{env_file}' already exists.")
    
    env_file.touch()

    # Create .giorgio/ and config.json
    giorgio_dir = root / ".giorgio"
    if giorgio_dir.exists():
        raise FileExistsError(f"Directory '{giorgio_dir}' already exists.")
    
    giorgio_dir.mkdir()

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
    scripts_dir = project_root / "scripts"
    if not scripts_dir.exists():
        raise FileNotFoundError(f"Scripts directory '{scripts_dir}' does not exist.")

    script_dir = scripts_dir / script
    if script_dir.exists():
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

    # Determine content
    if template is not None:
        # Replace __SCRIPT_PATH__ in provided template
        script_path_str = script.replace("\\", "/")
        content = template.replace("__SCRIPT_PATH__", script_path_str)
    else:
        # load built-in template file if available
        base_dir = Path(__file__).parent
        tpl_file = base_dir / "templates" / "script_template.py"
        if tpl_file.exists():
            raw = tpl_file.read_text(encoding="utf-8")
            script_path_str = script.replace("\\", "/")
            content = raw.replace("__SCRIPT_PATH__", script_path_str)
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
    
    giorgio_dir = root / ".giorgio"
    config_file = giorgio_dir / "config.json"
    scripts_dir = root / "scripts"

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file '{config_file}' not found.")
    
    if not scripts_dir.exists():
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

    print(f"Current project version: {project_version}")
    print(f"Installed Giorgio version: {installed_version}")

    if project_version == installed_version and not force:
        print("Project is already up-to-date.")
        return

    def validate_scripts() -> bool:
        """
        Validate all scripts in the 'scripts/' directory by importing them
        and checking that their CONFIG contains 'name' and 'description'.

        :return: True if all scripts pass validation, False otherwise.
        :rtype: bool
        """
        failed = []
        
        for script_path in scripts_dir.rglob("script.py"):
            rel_path = script_path.relative_to(scripts_dir).parent
            spec_path = script_path

            try:
                # Temporarily add scripts_dir to sys.path
                sys.path.insert(0, str(scripts_dir))
                
                module_name = ".".join(rel_path.parts + ("script",))
                spec = importlib.util.spec_from_file_location(module_name, spec_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)  # type: ignore

                # Check CONFIG
                cfg = getattr(module, "CONFIG", None)
                if not isinstance(cfg, dict) or "name" not in cfg or "description" not in cfg:
                    failed.append(str(rel_path))
            
            except Exception as e:
                failed.append(f"{rel_path} (error: {e})")
            
            finally:
                # Remove scripts_dir from sys.path if added
                if sys.path and sys.path[0] == str(scripts_dir):
                    sys.path.pop(0)

        if failed:
            print("Validation failed for the following scripts:")
            
            for fpath in failed:
                print(f"  - {fpath}")
            
            return False
        
        return True

    if force:
        confirm = True
    
    else:
        print("Running validation on all scripts...")
        
        if not validate_scripts():
            raise RuntimeError("Upgrade aborted due to validation failures.")
        
        # User confirmation
        confirm = questionary.confirm("All scripts validated successfully. Update project version?").ask()

    if confirm:
        config_data["giorgio_version"] = installed_version
        
        with config_file.open("w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
        
        print(f"Project upgraded to Giorgio version {installed_version}.")
    
    else:
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
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return MappingProxyType(config)
