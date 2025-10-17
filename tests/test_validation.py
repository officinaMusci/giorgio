import ast
from pathlib import Path
import pytest
from giorgio import validation

def _write_script(tmp_path: Path, rel_path: str, content: str) -> Path:
    path = tmp_path / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _codes(issues):
    return {issue.code for issue in issues}


def test_validate_script_missing_config_and_params_and_run(tmp_path):
    script = _write_script(tmp_path, "script.py", "")
    issues = validation.validate_script(script)
    codes = _codes(issues)
    assert "CONFIG_MISSING" in codes
    assert "PARAMS_MISSING" in codes
    assert "RUN_MISSING" in codes
    assert validation.has_errors(issues)


def test_config_not_dict_and_invalid_fields(tmp_path):
    content = """
CONFIG = 1
def run(context):
    pass
"""
    script = _write_script(tmp_path, "script.py", content)
    issues = validation.validate_script(script)
    codes = _codes(issues)
    assert "CONFIG_NOT_DICT" in codes

    # now test dict but invalid name/description
    content2 = """
CONFIG = {"name": "", "description": 123}
def run(context):
    pass
"""
    script2 = _write_script(tmp_path, "script2.py", content2)
    issues2 = validation.validate_script(script2)
    codes2 = _codes(issues2)
    assert "CONFIG_NAME_INVALID" in codes2
    assert "CONFIG_DESCRIPTION_INVALID" in codes2


def test_params_key_and_entry_validation(tmp_path):
    content = """
CONFIG = {"name": "n", "description": "d"}
PARAMS = {1: {}}
def run(context):
    pass
"""
    script = _write_script(tmp_path, "script.py", content)
    issues = validation.validate_script(script)
    codes = _codes(issues)
    assert "PARAM_KEY_INVALID" in codes

    content2 = """
CONFIG = {"name": "n", "description": "d"}
PARAMS = {"x": 1}
def run(context):
    pass
"""
    script2 = _write_script(tmp_path, "script2.py", content2)
    issues2 = validation.validate_script(script2)
    codes2 = _codes(issues2)
    assert "PARAM_ENTRY_NOT_DICT" in codes2


def test_param_entry_missing_type_and_description_and_flags_choices(tmp_path):
    content = """
CONFIG = {"name": "n", "description": "d"}
PARAMS = {
    "p": {}
}
def run(context):
    pass
"""
    script = _write_script(tmp_path, "script.py", content)
    issues = validation.validate_script(script)
    codes = _codes(issues)
    assert "PARAM_TYPE_MISSING" in codes
    assert "PARAM_DESCRIPTION_MISSING" in codes

    # test description invalid, flag not bool, choices not literal
    content2 = """
CONFIG = {"name": "n", "description": "d"}
PARAMS = {
    "p": {
        "type": "str",
        "description": 123,
        "required": "yes",
        "choices": [FOO]
    }
}
def run(context):
    pass
"""
    script2 = _write_script(tmp_path, "script2.py", content2)
    issues2 = validation.validate_script(script2)
    codes2 = _codes(issues2)
    assert "PARAM_DESCRIPTION_INVALID" in codes2
    assert "PARAM_FLAG_NOT_BOOL" in codes2
    assert "PARAM_CHOICES_NOT_LITERAL" in codes2


def test_run_function_variations(tmp_path):
    # missing run
    script = _write_script(tmp_path, "a.py", "CONFIG = {'name':'n','description':'d'}")
    issues = validation.validate_script(script)
    assert "RUN_MISSING" in _codes(issues)

    # run with no args
    script2 = _write_script(
        tmp_path,
        "b.py",
        "CONFIG = {'name':'n','description':'d'}\ndef run():\n    pass\n",
    )
    issues2 = validation.validate_script(script2)
    assert "RUN_SIGNATURE_INVALID" in _codes(issues2)

    # run first arg not named context
    script3 = _write_script(
        tmp_path,
        "c.py",
        "CONFIG = {'name':'n','description':'d'}\ndef run(foo):\n    pass\n",
    )
    issues3 = validation.validate_script(script3)
    assert "RUN_ARG_NAME" in _codes(issues3)


def test_validate_project_and_summarize_validation(tmp_path):
    # script 1: empty -> errors and warnings
    _write_script(tmp_path, "scripts/a/script.py", "")
    # script 2: has valid CONFIG but missing run -> yields PARAMS_MISSING (warning) and RUN_MISSING (error)
    _write_script(
        tmp_path,
        "scripts/b/script.py",
        "CONFIG = {'name': 'n', 'description': 'd'}\n",
    )

    results = validation.validate_project(tmp_path)
    # keys are relative paths
    expected_keys = {Path("scripts/a/script.py"), Path("scripts/b/script.py")}
    assert set(results.keys()) == expected_keys

    summary = validation.summarize_validation(results)
    assert summary.total_scripts == 2
    assert summary.has_messages
    assert summary.has_errors
    assert summary.has_warnings
    assert not summary.no_scripts