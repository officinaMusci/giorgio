import sys
from pathlib import Path
import os
import time
import signal
import threading
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from giorgio.execution_engine import ExecutionEngine, GiorgioCancellationError


def write_script(tmp_path: Path, name: str, content: str) -> None:
    """
    Write a script to the temporary path with the given name and content.

    :param tmp_path: The temporary path where the script will be written.
    :type tmp_path: Path
    :param name: The name of the script directory.
    :type name: str
    :param content: The content of the script file.
    :type content: str
    :return: None
    :rtype: None
    """
    
    script_dir = tmp_path / "scripts" / name
    script_dir.mkdir(parents=True, exist_ok=True)
    
    (script_dir / "__init__.py").write_text("", encoding="utf-8")
    (script_dir / "script.py").write_text(content, encoding="utf-8")


def test_run_no_params(tmp_path, capsys):
    write_script(tmp_path, "noparams", """
PARAMS = {}
def run(context):
    print("hello")
""")
    
    engine = ExecutionEngine(tmp_path)
    
    with pytest.raises(RuntimeError):
        engine.run_script("noparams", cli_args=None)
    
    engine.run_script("noparams", cli_args={})
    captured = capsys.readouterr()
    assert "hello" in captured.out


def test_required_param_missing(tmp_path):
    write_script(tmp_path, "required", """
PARAMS = {
    "x": {"type": int, "required": True}
}
def run(context):
    pass
""")
    
    engine = ExecutionEngine(tmp_path)
    with pytest.raises(RuntimeError):
        engine.run_script("required", cli_args={})


def test_required_param_provided(tmp_path, capsys):
    write_script(tmp_path, "provided", """
PARAMS = {
    "x": {"type": int, "required": True}
}
def run(context):
    print(context.params["x"])
""")
    
    engine = ExecutionEngine(tmp_path)
    engine.run_script("provided", cli_args={"x": "5"})
    captured = capsys.readouterr()
    assert captured.out.strip() == "5"


def test_default_param(tmp_path, capsys):
    write_script(tmp_path, "default", """
PARAMS = {
    "x": {"type": int, "default": 7}
}
def run(context):
    print(context.params["x"])
""")
    
    engine = ExecutionEngine(tmp_path)
    engine.run_script("default", cli_args={})
    captured = capsys.readouterr()
    assert captured.out.strip() == "7"


def test_invalid_type(tmp_path):
    write_script(tmp_path, "badtype", """
PARAMS = {
    "x": {"type": int, "required": True}
}
def run(context):
    pass
""")
    
    engine = ExecutionEngine(tmp_path)

    with pytest.raises(ValueError):
        engine.run_script("badtype", cli_args={"x": "abc"})


def test_invalid_choice(tmp_path):
    write_script(tmp_path, "choice", """
PARAMS = {
    "x": {"type": str, "choices": ["a", "b"], "required": True}
}
def run(context):
    pass
""")
    
    engine = ExecutionEngine(tmp_path)

    with pytest.raises(ValueError):
        engine.run_script("choice", cli_args={"x": "c"})


def test_env_default(tmp_path, capsys, monkeypatch):
    write_script(tmp_path, "env", """
PARAMS = {
    "x": {"type": str, "default": "${MYVAR}"}
}
def run(context):
    print(context.params["x"])
""")
    
    # simulate .env load
    monkeypatch.setenv("MYVAR", "hello_env")
    engine = ExecutionEngine(tmp_path)
    engine.env["MYVAR"] = "hello_env"
    engine.run_script("env", cli_args={})
    captured = capsys.readouterr()
    assert captured.out.strip() == "hello_env"


def test_add_params_forbidden(tmp_path):
    write_script(tmp_path, "add", """
PARAMS = {}
def run(context):
    context.add_params({"y": {"type": int}})
""")
    
    engine = ExecutionEngine(tmp_path)

    with pytest.raises(RuntimeError):
        engine.run_script("add", cli_args={})


def test_boolean_conversion(tmp_path, capsys):
    write_script(tmp_path, "bool", """
PARAMS = {
    "flag": {"type": bool, "required": True}
}
def run(context):
    print(context.params["flag"])
""")
    
    engine = ExecutionEngine(tmp_path)

    # false values
    for raw in ("false", "0", "no", "n"):
        engine.run_script("bool", cli_args={"flag": raw})
        captured = capsys.readouterr()
        assert captured.out.strip() == "False"

    # true values
    for raw in ("true", "1", "yes", "y"):
        engine.run_script("bool", cli_args={"flag": raw})
        captured = capsys.readouterr()
        assert captured.out.strip() == "True"


def test_noninteractive_requires_cli_args(tmp_path):
    write_script(tmp_path, "mustcli", """
PARAMS = {}
def run(context):
    pass
""")
    engine = ExecutionEngine(tmp_path)

    with pytest.raises(RuntimeError):
        engine.run_script("mustcli", cli_args=None)


@pytest.mark.skipif(sys.platform == "win32", reason="SIGINT handling is unreliable on Windows")
def test_cancellation(tmp_path, capsys):
    write_script(tmp_path, "loop", """
import time
from giorgio.execution_engine import GiorgioCancellationError
PARAMS = {}
def run(context):
    try:
        while True:
            time.sleep(0.1)
            print("Running...")
    except GiorgioCancellationError:
        print("Script execution cancelled.")
""")
    pid = os.getpid()
    def send_sigint_after_delay():
        time.sleep(0.5)
        os.kill(pid, signal.SIGINT)
    threading.Thread(target=send_sigint_after_delay, daemon=True).start()

    engine = ExecutionEngine(tmp_path)
    engine.run_script("loop", cli_args={})
    out = capsys.readouterr().out
    assert "Script execution cancelled." in out


def test_cancellation(tmp_path, capsys):
    write_script(tmp_path, "loop", """
from giorgio.execution_engine import GiorgioCancellationError
PARAMS = {}
def run(context):
    raise GiorgioCancellationError()
""")
    engine = ExecutionEngine(tmp_path)
    engine.run_script("loop", cli_args={})
    out = capsys.readouterr().out
    assert "Script execution cancelled." in out