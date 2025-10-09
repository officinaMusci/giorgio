import sys
import json
from pathlib import Path

import pytest
from typer import BadParameter
from typer.testing import CliRunner
import questionary
import giorgio.project_manager as pm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from giorgio import cli
from giorgio.cli import app
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
    result = runner.invoke(app, ["init", str(project_dir)])
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

def test_new_script_ai(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    # Patch AIScriptingClient to avoid real API call
    class DummyAIScriptingClient:
        def __init__(self, project_root):
            pass
        def generate_script(self, prompt):
            assert prompt == "do something cool"
            return "# ai generated script"
    monkeypatch.setattr("giorgio.cli.AIScriptingClient", DummyAIScriptingClient)
    result = runner.invoke(app, ["new", "aiscript", "--ai-prompt", "do something cool"])
    assert result.exit_code == 0
    script_dir = tmp_path / "scripts" / "aiscript"
    assert script_dir.is_dir()
    script_file = script_dir / "script.py"
    assert script_file.exists()
    assert "# ai generated script" in script_file.read_text()

def test_new_exists_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    runner.invoke(app, ["new", "dup"])
    result = runner.invoke(app, ["new", "dup"])
    assert result.exit_code != 0
    assert "Error creating script" in result.stdout

def test_new_ai_config_error(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    class DummyAIScriptingClient:
        def __init__(self, project_root):
            raise RuntimeError("bad config")
    monkeypatch.setattr("giorgio.cli.AIScriptingClient", DummyAIScriptingClient)
    result = runner.invoke(app, ["new", "failai", "--ai-prompt", "x"])
    assert result.exit_code == 1
    assert "bad config" in result.stdout

def test_new_ai_generation_error(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    class DummyAIScriptingClient:
        def __init__(self, project_root):
            pass
        def generate_script(self, prompt):
            raise Exception("ai fail")
    monkeypatch.setattr("giorgio.cli.AIScriptingClient", DummyAIScriptingClient)
    result = runner.invoke(app, ["new", "failai", "--ai-prompt", "x"])
    assert result.exit_code == 1
    assert "Error creating script: ai fail" in result.stdout


def test_cli_run_and_parameters(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    script_dir = tmp_path / "scripts" / "hello"
    script_dir.mkdir(parents=True)
    (script_dir / "__init__.py").write_text("", encoding="utf-8")
    (script_dir / "script.py").write_text(
        "PARAMS = {'x': {'type': int, 'required': True}}\n"
        "def run(context): print(context.params['x'])\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["run", "hello"])
    assert result.exit_code != 0
    assert result.exception is not None
    assert "Missing required parameter" in str(result.exception)
    result = runner.invoke(app, ["run", "hello", "--param", "x=42"])
    assert result.exit_code == 0
    assert "42" in result.stdout


def test_version_mismatch_warning_on_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    config_path = tmp_path / ".giorgio" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["giorgio_version"] = "1.0.0"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    script_dir = tmp_path / "scripts" / "hello"
    script_dir.mkdir(parents=True)
    (script_dir / "__init__.py").write_text("", encoding="utf-8")
    (script_dir / "script.py").write_text(
        "PARAMS = {'x': {'type': int, 'required': True}}\n"
        "def run(context): print(context.params['x'])\n",
        encoding="utf-8",
    )

    monkeypatch.setattr("giorgio.project_manager._get_version", lambda pkg: "2.0.0")

    result = runner.invoke(app, ["run", "hello", "--param", "x=7"])
    assert result.exit_code == 0
    assert "⚠️  Project expects Giorgio 1.0.0, but version 2.0.0 is installed." in result.stdout


def test_cli_upgrade_command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    script_dir = tmp_path / "scripts" / "good"
    script_dir.mkdir(parents=True)
    (script_dir / "__init__.py").write_text("", encoding="utf-8")
    (script_dir / "script.py").write_text(
        "CONFIG = {'name': 'good', 'description': 'desc'}\nPARAMS = {}\ndef run(context): pass\n",
        encoding="utf-8",
    )

    config_path = tmp_path / ".giorgio" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["giorgio_version"] = "1.0.0"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    monkeypatch.setattr("giorgio.project_manager._get_version", lambda pkg: "3.2.1")
    monkeypatch.setattr(
        pm.questionary,
        "confirm",
        lambda msg: type("StubQ", (), {"ask": lambda self: True})(),
    )

    result = runner.invoke(app, ["upgrade"])
    assert result.exit_code == 0
    assert "Project upgraded to Giorgio version 3.2.1." in result.stdout

    updated = json.loads(config_path.read_text(encoding="utf-8"))
    assert updated["giorgio_version"] == "3.2.1"


def test_cli_upgrade_force_skips_validation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    bad_dir = tmp_path / "scripts" / "bad"
    bad_dir.mkdir(parents=True)
    (bad_dir / "__init__.py").write_text("", encoding="utf-8")
    (bad_dir / "script.py").write_text("def run(context): pass\n", encoding="utf-8")

    config_path = tmp_path / ".giorgio" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["giorgio_version"] = "1.0.0"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    monkeypatch.setattr("giorgio.project_manager._get_version", lambda pkg: "4.5.6")

    result = runner.invoke(app, ["upgrade", "--force"])
    assert result.exit_code == 0
    assert "Project upgraded to Giorgio version 4.5.6." in result.stdout

    updated = json.loads(config_path.read_text(encoding="utf-8"))
    assert updated["giorgio_version"] == "4.5.6"


def test_cli_start(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    script_dir = tmp_path / "scripts" / "s"
    script_dir.mkdir(parents=True)
    (script_dir / "__init__.py").write_text("", encoding="utf-8")
    (script_dir / "script.py").write_text(
        "PARAMS = {}\ndef run(context): print('ok')\n", encoding="utf-8"
    )
    
    # Patch questionary.select to simulate user selecting the script
    def fake_select(message, choices, default=None):
        class DummyQuestion:
            def ask(inner_self):
                # Select the script by its title containing "s"
                for c in choices:
                    if "s" in c.title:
                        return c.value
                return choices[0].value
        return DummyQuestion()
    monkeypatch.setattr(questionary, "select", fake_select)
    result = runner.invoke(app, ["start"])
    assert result.exit_code == 0
    assert "ok" in result.stdout


def test_run_script_handles_exception(monkeypatch, tmp_path):
    class DummyEngine:
        def run_script(self, *a, **kw):
            raise RuntimeError("fail run")

    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    monkeypatch.setattr(cli, "ExecutionEngine", lambda *a, **k: DummyEngine())
    result = runner.invoke(app, ["run", "noscript"])
    assert result.exit_code != 0
    assert result.exception is not None
    assert "fail run" in str(result.exception)


def test_start_no_ui_renderers(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    monkeypatch.setattr(cli, "_discover_ui_renderers", lambda: {})
    result = runner.invoke(app, ["start"])
    assert result.exit_code == 1
    assert "No UI renderers available." in result.output


def test_start_unknown_ui_renderer(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    monkeypatch.setattr(cli, "_discover_ui_renderers", lambda: {"foo": object})
    result = runner.invoke(app, ["start", "--ui", "bar"])
    assert result.exit_code == 1
    assert "Unknown UI renderer: bar" in result.output


def test_start_no_scripts(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    class DummyRenderer:
        def __init__(self): pass
        def list_scripts(self, scripts): return None
        def prompt_params(self, s, e): return {}
    monkeypatch.setattr(cli, "_discover_ui_renderers", lambda: {"dummy": DummyRenderer})
    result = runner.invoke(app, ["start"])
    assert result.exit_code == 1
    assert "No scripts found in scripts/ directory." in result.stdout


def test_start_no_script_selected(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    script_dir = tmp_path / "scripts" / "foo"
    script_dir.mkdir(parents=True)
    (script_dir / "script.py").write_text("PARAMS={}\ndef run(context): pass\n")
    class DummyRenderer:
        def __init__(self): pass
        def list_scripts(self, scripts): return None
        def prompt_params(self, s, e): return {}
    monkeypatch.setattr(cli, "_discover_ui_renderers", lambda: {"dummy": DummyRenderer})
    result = runner.invoke(app, ["start"])
    assert result.exit_code == 0
    assert "No script selected." in result.stdout


def test_start_keyboard_interrupt(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    script_dir = tmp_path / "scripts" / "foo"
    script_dir.mkdir(parents=True)
    (script_dir / "script.py").write_text("PARAMS={}\ndef run(context): pass\n")
    class DummyRenderer:
        def __init__(self): pass
        def list_scripts(self, scripts): return "foo"
        def prompt_params(self, s, e): return {}
    class DummyEngine:
        def run_script(self, *a, **k):
            raise KeyboardInterrupt()
    monkeypatch.setattr(cli, "_discover_ui_renderers", lambda: {"dummy": DummyRenderer})
    monkeypatch.setattr(cli, "ExecutionEngine", lambda *a, **k: DummyEngine())
    result = runner.invoke(app, ["start"])
    assert result.exit_code == 1
    assert "Execution interrupted by user." in result.stdout


def test_start_script_execution_error(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    script_dir = tmp_path / "scripts" / "foo"
    script_dir.mkdir(parents=True)
    (script_dir / "script.py").write_text("PARAMS={}\ndef run(context): pass\n")
    class DummyRenderer:
        def __init__(self): pass
        def list_scripts(self, scripts): return "foo"
        def prompt_params(self, s, e): return {}
    class DummyEngine:
        def run_script(self, *a, **k):
            raise Exception("fail exec")
    monkeypatch.setattr(cli, "_discover_ui_renderers", lambda: {"dummy": DummyRenderer})
    monkeypatch.setattr(cli, "ExecutionEngine", lambda *a, **k: DummyEngine())
    result = runner.invoke(app, ["start"])
    assert result.exit_code != 0
    assert result.exception is not None
    assert "fail exec" in str(result.exception)


def test_init_error(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    def fail_init(*a, **k): raise Exception("fail init")
    monkeypatch.setattr(cli, "initialize_project", fail_init)
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 1
    assert "Error initializing project: fail init" in result.stdout


def test_new_error(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    def fail_create(*a, **k): raise Exception("fail new")
    monkeypatch.setattr(cli, "create_script", fail_create)
    result = runner.invoke(app, ["new", "fail"])
    assert result.exit_code == 1
    assert "Error creating script: fail new" in result.stdout


def test_parse_params_valid_and_edge_cases():
    # Covers valid, empty, value with equals, duplicate keys, leading/trailing spaces
    params = ["foo=1", "bar=hello", "baz=3.14"]
    assert _parse_params(params) == {"foo": "1", "bar": "hello", "baz": "3.14"}
    assert _parse_params([]) == {}
    params = ["key=some=value=with=equals"]
    assert _parse_params(params) == {"key": "some=value=with=equals"}
    params = [" foo = bar ", "baz= qux "]
    assert _parse_params(params) == {" foo ": " bar ", "baz": " qux "}
    params = ["foo=1", "foo=2"]
    assert _parse_params(params) == {"foo": "2"}


def test_parse_params_invalid_format():
    # Covers both generic and BadParameter exception
    with pytest.raises(Exception):
        _parse_params(["foo", "bar=2"])
    params = ["foo", "bar=baz"]
    with pytest.raises(BadParameter) as excinfo:
        _parse_params(params)
    assert "Invalid parameter format" in str(excinfo.value)


def test_discover_ui_renderers(monkeypatch, capsys):
    # Covers both normal and load error
    class DummyEP:
        def __init__(self, name):
            self.name = name
        def load(self):
            if self.name == "bad":
                raise RuntimeError("fail")
            return str

    def fake_entry_points(group=None):
        if group == "giorgio.ui_renderers":
            return [DummyEP("dummy"), DummyEP("bad")]
        return []

    monkeypatch.setattr("giorgio.cli.entry_points", fake_entry_points)
    renderers = _discover_ui_renderers()
    assert isinstance(renderers, dict)
    assert "dummy" in renderers
    assert renderers["dummy"] is str
    assert "bad" not in renderers
    captured = capsys.readouterr()
    assert "Warning: could not load UI plugin" in captured.out
