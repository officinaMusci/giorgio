import sys
from pathlib import Path
import json
import shutil
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import giorgio.project_manager as pm
from giorgio.project_manager import initialize_project, create_script, upgrade_project


@pytest.fixture
def temp_project(tmp_path):
    """
    Create a temporary directory for each test.

    :param tmp_path: The temporary path provided by pytest.
    :type tmp_path: Path
    :return: Path to the temporary project directory.
    :rtype: Path
    """
    
    project_root = tmp_path / "my_giorgio_project"
    project_root.mkdir()
    
    return project_root


def test_initialize_project_creates_structure(temp_project):
    # Run initialize_project
    initialize_project(temp_project, project_name="TestProject")

    # Verify 'scripts/' exists
    scripts_dir = temp_project / "scripts"
    assert scripts_dir.is_dir(), "scripts/ directory was not created."

    # Verify 'modules/' exists with __init__.py
    modules_dir = temp_project / "modules"
    assert modules_dir.is_dir(), "modules/ directory was not created."
    assert (modules_dir / "__init__.py").is_file(), "__init__.py in modules/ missing."

    # Verify '.env' exists and is empty
    env_file = temp_project / ".env"
    assert env_file.is_file(), ".env file was not created."
    assert env_file.stat().st_size == 0, ".env file should be empty upon init."

    # Verify requirements.txt exists with default dependency
    requirements_file = temp_project / "requirements.txt"
    assert requirements_file.is_file(), "requirements.txt was not created."
    assert requirements_file.read_text(encoding="utf-8") == "giorgio\n"

    # Verify '.giorgio/config.json' exists with correct keys
    giorgio_dir = temp_project / ".giorgio"
    assert giorgio_dir.is_dir(), ".giorgio directory was not created."

    config_file = giorgio_dir / "config.json"
    assert config_file.is_file(), "config.json was not created."

    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert "giorgio_version" in data, "giorgio_version not in config.json"
    assert "module_paths" in data, "module_paths not in config.json"
    assert "logging" in data, "logging not in config.json"
    assert data.get("logging") == {"level": "warning"}, "Default logging level should be 'warning'"
    assert data.get("module_paths") == ["modules"]
    assert data.get("project_name") == "TestProject"


def test_initialize_project_errors_if_already_exists(temp_project):
    # First initialization succeeds
    initialize_project(temp_project)

    # Second call should raise FileExistsError
    with pytest.raises(FileExistsError):
        initialize_project(temp_project)


def test_create_script_happy_path(temp_project):
    # First, initialize the project
    initialize_project(temp_project)

    # Use an inline template with the placeholder
    tpl = "CONFIG = {'name': '__SCRIPT_PATH__'}"
    create_script(temp_project, "foo/bar", template=tpl)

    script_folder = temp_project / "scripts" / "foo" / "bar"
    assert script_folder.is_dir(), "Script folder was not created."

    script_file = script_folder / "script.py"
    assert script_file.is_file(), "script.py was not created."

    content = script_file.read_text(encoding="utf-8")
    assert "__SCRIPT_PATH__" not in content
    assert "'foo/bar'" in content, "CONFIG name placeholder not replaced."


def test_create_script_errors_if_scripts_dir_missing(temp_project):
    # Do not initialize: scripts/ does not exist
    with pytest.raises(FileNotFoundError):
        create_script(temp_project, "newscript")


def test_create_script_errors_if_already_exists(temp_project):
    initialize_project(temp_project)
    create_script(temp_project, "foo")

    with pytest.raises(FileExistsError):
        create_script(temp_project, "foo")


def test_upgrade_project_force_updates_version(temp_project, monkeypatch):
    # Initialize and write an old version in config.json
    initialize_project(temp_project)
    config_file = temp_project / ".giorgio" / "config.json"
    data = json.loads(config_file.read_text(encoding="utf-8"))
    data["giorgio_version"] = "0.0.1"
    config_file.write_text(json.dumps(data), encoding="utf-8")

    # Monkeypatch giorgio.project_manager._get_version to simulate installed
    # version "9.9.9"
    monkeypatch.setattr(
        "giorgio.project_manager._get_version",
        lambda pkg: "9.9.9"
    )

    # Monkeypatch questionary.confirm to always return True
    # This simulates user confirming the upgrade
    monkeypatch.setattr(
        pm.questionary,
        "confirm",
        lambda msg: type("StubQ", (), {"ask": lambda self: True})()
    )

    # Force update without validation
    upgrade_project(temp_project, force=True)

    updated = json.loads(config_file.read_text(encoding="utf-8"))
    assert updated["giorgio_version"] == "9.9.9"


def test_upgrade_project_validation_failure(temp_project, monkeypatch):
    # Initialize project and create an invalid script (missing CONFIG keys)
    initialize_project(temp_project)

    # Create scripts/bad/script.py with no CONFIG
    bad_folder = temp_project / "scripts" / "bad"
    bad_folder.mkdir(parents=True)
    (bad_folder / "__init__.py").touch()
    (bad_folder / "script.py").write_text("def run(context): pass\n", encoding="utf-8")

    # Monkeypatch importlib.metadata.version to a higher version
    monkeypatch.setattr(
        "giorgio.project_manager._get_version",
        lambda pkg: "9.9.9"
    )

    # Monkeypatch questionary.confirm to always return True
    # This simulates user confirming the upgrade
    monkeypatch.setattr(
        pm.questionary,
        "confirm",
        lambda msg: type("StubQ", (), {"ask": lambda self: True})()
    )

    with pytest.raises(RuntimeError):
        upgrade_project(temp_project, force=False)


def test_upgrade_project_happy_path(temp_project, monkeypatch):
    # Initialize project and create a valid script
    initialize_project(temp_project)

    good_folder = temp_project / "scripts" / "good"
    good_folder.mkdir(parents=True)
    (good_folder / "__init__.py").touch()

    # script.py has valid CONFIG
    (good_folder / "script.py").write_text(
        "CONFIG = {'name': 'good', 'description': 'desc'}\n"
        "PARAMS = {}\n"
        "def run(context): pass\n",
        encoding="utf-8"
    )

    # Monkeypatch installed version to "2.3.4"
    monkeypatch.setattr(
        "giorgio.project_manager._get_version",
        lambda pkg: "2.3.4"
    )

    # Monkeypatch questionary.confirm to always return True
    # This simulates user confirming the upgrade
    monkeypatch.setattr(
        pm.questionary,
        "confirm",
        lambda msg: type("StubQ", (), {"ask": lambda self: True})()
    )

    upgrade_project(temp_project, force=False)

    config_file = temp_project / ".giorgio" / "config.json"
    updated = json.loads(config_file.read_text(encoding="utf-8"))
    assert updated["giorgio_version"] == "2.3.4"


def test_initialize_project_creates_giorgio_dir_and_config(temp_project):
    initialize_project(temp_project)
    giorgio_dir = temp_project / ".giorgio"
    config_file = giorgio_dir / "config.json"
    assert giorgio_dir.is_dir()
    assert config_file.is_file()
    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert "giorgio_version" in data
    assert "module_paths" in data


def test_initialize_project_raises_if_scripts_exists(temp_project):
    (temp_project / "scripts").mkdir()
    with pytest.raises(FileExistsError):
        initialize_project(temp_project)


def test_initialize_project_raises_if_modules_exists(temp_project):
    (temp_project / "modules").mkdir()
    with pytest.raises(FileExistsError):
        initialize_project(temp_project)


def test_initialize_project_raises_if_env_exists(temp_project):
    (temp_project / ".env").touch()
    with pytest.raises(FileExistsError):
        initialize_project(temp_project)


def test_initialize_project_raises_if_giorgio_dir_exists(temp_project):
    (temp_project / ".giorgio").mkdir()
    with pytest.raises(FileExistsError):
        initialize_project(temp_project)


def test_initialize_project_raises_if_requirements_exists(temp_project):
    (temp_project / "requirements.txt").write_text("custom\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        initialize_project(temp_project)

def test_create_script_creates_init_at_each_level(temp_project, tmp_path, monkeypatch):
    initialize_project(temp_project)
    # Patch template file to a known content in a temp dir
    template_dir = tmp_path / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    template_file = template_dir / "script_template.py"
    template_file.write_text("CONFIG = {'name': '__SCRIPT_PATH__'}", encoding="utf-8")
    monkeypatch.setattr("giorgio.project_manager.__file__", str(tmp_path / "project_manager.py"))
    monkeypatch.setattr("giorgio.project_manager.Path", lambda *args, **kwargs: Path(*args, **kwargs) if args and args[0] != "templates" else template_dir)
    create_script(temp_project, "a/b/c")
    assert (temp_project / "scripts" / "a" / "__init__.py").is_file()
    assert (temp_project / "scripts" / "a" / "b" / "__init__.py").is_file()
    assert (temp_project / "scripts" / "a" / "b" / "c" / "__init__.py").is_file()
    assert (temp_project / "scripts" / "a" / "b" / "c" / "__init__.py").is_file()
    
    
def test_create_script_replaces_placeholder(temp_project):
    initialize_project(temp_project)

    # Inline template containing the placeholder
    tpl = "CONFIG = {'name': '__SCRIPT_PATH__'}\n"
    create_script(temp_project, "foo/bar", template=tpl)

    script_file = temp_project / "scripts" / "foo" / "bar" / "script.py"
    content = script_file.read_text(encoding="utf-8")
    assert "__SCRIPT_PATH__" not in content
    assert "'foo/bar'" in content


def test_upgrade_project_prints_up_to_date(temp_project, capsys, monkeypatch):
    initialize_project(temp_project)
    
    # Set project version to match the mocked installed version
    config_file = temp_project / ".giorgio" / "config.json"
    data = json.loads(config_file.read_text(encoding="utf-8"))
    data["giorgio_version"] = "0.0.0"
    config_file.write_text(json.dumps(data), encoding="utf-8")
    
    monkeypatch.setattr("giorgio.project_manager._get_version", lambda pkg: "0.0.0")
    # Patch questionary.confirm to avoid interactive prompt
    monkeypatch.setattr(
        pm.questionary,
        "confirm",
        lambda msg: type("StubQ", (), {"ask": lambda self: True})()
    )
    upgrade_project(temp_project, force=False)
    out = capsys.readouterr().out
    assert "Project is already up-to-date." in out
    config_file = temp_project / ".giorgio" / "config.json"
    config_file.unlink()
    with pytest.raises(FileNotFoundError):
        upgrade_project(temp_project)


def test_upgrade_project_raises_if_scripts_missing(temp_project):
    initialize_project(temp_project)
    scripts_dir = temp_project / "scripts"
    shutil.rmtree(scripts_dir)
    with pytest.raises(FileNotFoundError):
        upgrade_project(temp_project)


def test_upgrade_project_validation_fails_on_bad_config(temp_project, monkeypatch):
    initialize_project(temp_project)
    bad_folder = temp_project / "scripts" / "bad"
    bad_folder.mkdir(parents=True)
    (bad_folder / "__init__.py").touch()
    (bad_folder / "script.py").write_text("CONFIG = {'name': 'bad'}", encoding="utf-8")
    monkeypatch.setattr("giorgio.project_manager._get_version", lambda pkg: "1.2.3")
    monkeypatch.setattr(
        pm.questionary,
        "confirm",
        lambda msg: type("StubQ", (), {"ask": lambda self: True})()
    )
    with pytest.raises(RuntimeError):
        upgrade_project(temp_project, force=False)


def test_upgrade_project_confirm_false_does_not_update(temp_project, monkeypatch):
    initialize_project(temp_project)
    good_folder = temp_project / "scripts" / "good"
    good_folder.mkdir(parents=True)
    (good_folder / "__init__.py").touch()
    (good_folder / "script.py").write_text(
        "CONFIG = {'name': 'good', 'description': 'desc'}\nPARAMS = {}\ndef run(context): pass\n",
        encoding="utf-8"
    )
    monkeypatch.setattr("giorgio.project_manager._get_version", lambda pkg: "2.3.4")
    monkeypatch.setattr(
        pm.questionary,
        "confirm",
        lambda msg: type("StubQ", (), {"ask": lambda self: False})()
    )
    config_file = temp_project / ".giorgio" / "config.json"
    old_data = json.loads(config_file.read_text(encoding="utf-8"))
    upgrade_project(temp_project, force=False)
    new_data = json.loads(config_file.read_text(encoding="utf-8"))
    assert new_data["giorgio_version"] == old_data["giorgio_version"]