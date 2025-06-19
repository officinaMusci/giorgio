import sys
import json
from pathlib import Path

from typer.testing import CliRunner
import questionary

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from giorgio.cli import app

runner = CliRunner()


def test_init_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert (tmp_path / "scripts").is_dir()
    assert (tmp_path / "modules").is_dir()
    assert (tmp_path / ".giorgio").is_dir()
    
    config_path = tmp_path / ".giorgio" / "config.json"
    assert config_path.exists()
    
    cfg = json.loads(config_path.read_text())
    assert "giorgio_version" in cfg
    assert "module_paths" in cfg


def test_init_named(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project_dir = tmp_path / "myproj"
    result = runner.invoke(app, ["init", "--name", str(project_dir)])
    assert result.exit_code == 0
    assert project_dir.is_dir()
    assert (project_dir / "scripts").is_dir()
    assert (project_dir / "modules").is_dir()


def test_new_script(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["new", "myscript"])
    assert result.exit_code == 0
    
    script_dir = tmp_path / "scripts" / "myscript"
    assert script_dir.is_dir()
    assert (script_dir / "script.py").exists()


def test_new_exists_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["new", "dup"])
    result = runner.invoke(app, ["new", "dup"])
    
    assert result.exit_code != 0
    assert "Error creating script" in result.stdout


def test_cli_run_and_parameters(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    
    # Create a script that requires an int param 'x'
    script_dir = tmp_path / "scripts" / "hello"
    script_dir.mkdir(parents=True)
    
    (script_dir / "__init__.py").write_text("", encoding="utf-8")
    (script_dir / "script.py").write_text(
        "PARAMS = {'x': {'type': int, 'required': True}}\n"
        "def run(context): print(context.params['x'])\n",
        encoding="utf-8",
    )
    
    # Missing param should error
    result = runner.invoke(app, ["run", "hello"])
    assert result.exit_code == 1
    assert "Missing required parameter" in result.stdout
    
    # Correct param prints value
    result = runner.invoke(app, ["run", "hello", "--param", "x=42"])
    assert result.exit_code == 0
    assert "42" in result.stdout


def test_cli_start(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    
    # Create a script with no params
    script_dir = tmp_path / "scripts" / "s"
    script_dir.mkdir(parents=True)
    
    (script_dir / "__init__.py").write_text("", encoding="utf-8")
    (script_dir / "script.py").write_text(
        "PARAMS = {}\ndef run(context): print('ok')\n", encoding="utf-8"
    )
    
    # Stub selection to 's'
    monkeypatch.setattr(
        questionary,
        "select",
        lambda *args, **kwargs: type("Q", (), {"ask": lambda self: "s"})(),
    )
    result = runner.invoke(app, ["start"])
    assert result.exit_code == 0
    assert "ok" in result.stdout
