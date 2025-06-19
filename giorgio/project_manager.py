import json
import sys
from pathlib import Path
from importlib.metadata import version as _get_version, PackageNotFoundError
import questionary
import importlib.util


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
        "module_paths": ["modules"]
    }
    
    if project_name:
        default_config["project_name"] = project_name

    with config_file.open("w", encoding="utf-8") as f:
        json.dump(default_config, f, indent=2)


def create_script(root: Path, script_relative_path: str) -> None:
    """
    Scaffold a new script under the 'scripts/' directory.

    Creates a folder at scripts/<script_relative_path>/ containing:
      - __init__.py         (to allow importing if needed)
      - script.py           (with boilerplate read from a template)

    :param root: Path to the project root.
    :type root: Path
    :param script_relative_path: Relative path under 'scripts/' where the new
    script should be created (e.g., "data/clean").
    :type script_relative_path: str
    :raises FileNotFoundError: If the 'scripts/' directory does not exist.
    :raises FileExistsError: If the target script directory already exists.
    :raises FileNotFoundError: If the script template file does not exist.
    """

    scripts_dir = root / "scripts"
    if not scripts_dir.exists():
        raise FileNotFoundError(f"'scripts/' directory not found in {root}.")

    target_dir = scripts_dir / script_relative_path
    if target_dir.exists():
        raise FileExistsError(f"Script directory '{target_dir}' already exists.")

    # Create nested directories (data/clean, etc.)
    target_dir.mkdir(parents=True, exist_ok=False)
    
    # Create an __init__.py at each level to allow package import if needed
    # Example: scripts/data/__init__.py and scripts/data/clean/__init__.py
    parts = target_dir.relative_to(scripts_dir).parts
    cumulative = scripts_dir
    
    for part in parts:
        cumulative = cumulative / part
        init_path = cumulative / "__init__.py"
        
        if not init_path.exists():
            init_path.touch()

    # Create script.py from the template
    script_file = target_dir / "script.py"
    template_dir = Path(__file__).parent / "templates"
    template_file = template_dir / "script_template.py"
    if not template_file.exists():
        raise FileNotFoundError(f"Template file '{template_file}' not found.")

    # Read the template content and replace the __SCRIPT_PATH__ placeholder
    template_content = template_file.read_text(encoding="utf-8")
    boilerplate = template_content.replace("__SCRIPT_PATH__", script_relative_path)

    with script_file.open("w", encoding="utf-8") as f:
        f.write(boilerplate)


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
        print(f"Current project version: {project_version}")
        print(f"Installed Giorgio version: {installed_version}")
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

