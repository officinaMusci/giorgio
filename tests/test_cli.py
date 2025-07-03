import sys
import json
from pathlib import Path

from typer.testing import CliRunner
import questionary

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from giorgio.cli import app
import pytest
from typer.testing import CliRunner
from giorgio.cli import _parse_params, _discover_ui_renderers

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


def test_parse_params_valid():
    params = ["foo=1", "bar=hello", "baz=3.14"]
    result = _parse_params(params)
    assert result == {"foo": "1", "bar": "hello", "baz": "3.14"}


def test_parse_params_empty():
    result = _parse_params([])
    assert result == {}


def test_parse_params_invalid_format():
    with pytest.raises(Exception):
        _parse_params(["foo", "bar=2"])


def test_discover_ui_renderers_returns_dict(monkeypatch):
    class DummyEP:
        def __init__(self, name):
            self.name = name
        def load(self):
            return str

    def fake_entry_points(group=None):
        if group == "giorgio.ui_renderers":
            return [DummyEP("dummy")]
        return []

    monkeypatch.setattr("giorgio.cli.entry_points", fake_entry_points)
    renderers = _discover_ui_renderers()
    assert isinstance(renderers, dict)
    assert "dummy" in renderers
    assert renderers["dummy"] is str


def test_discover_ui_renderers_handles_load_error(monkeypatch, capsys):
    class DummyEP:
        def __init__(self, name):
            self.name = name
        def load(self):
            raise RuntimeError("fail")

    def fake_entry_points(group=None):
        if group == "giorgio.ui_renderers":
            return [DummyEP("bad")]
        return []

    monkeypatch.setattr("giorgio.cli.entry_points", fake_entry_points)
    renderers = _discover_ui_renderers()
    assert "bad" not in renderers
    captured = capsys.readouterr()
    assert "Warning: could not load UI plugin" in captured.out
