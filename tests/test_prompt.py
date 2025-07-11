import pytest
from pathlib import Path
from giorgio import prompt


@pytest.fixture
def mock_questionary(monkeypatch):
    class MockQuestionary:
        def __init__(self):
            self.confirm_called = []
            self.select_called = []
            self.checkbox_called = []
            self.path_called = []
            self.text_called = []
            self.password_called = []

        def confirm(self, message, default):
            self.confirm_called.append((message, default))
            class Confirm:
                def ask(inner_self):
                    return True
            return Confirm()

        def select(self, message, choices, default=None):
            self.select_called.append((message, choices, default))
            class Select:
                def ask(inner_self):
                    # Return the value of the first choice
                    return choices[0].value if choices else None
            return Select()

        def checkbox(self, message, choices, validate=None):
            self.checkbox_called.append((message, choices))
            class Checkbox:
                def ask(inner_self):
                    # Return the values of checked choices
                    return [c.value for c in choices if getattr(c, "checked", False)]
            return Checkbox()

        def path(self, message, default, validate=None):
            self.path_called.append((message, default))
            class PathPrompt:
                def ask(inner_self):
                    return default or "/tmp/test.txt"
            return PathPrompt()

        def text(self, message, default, validate=None):
            self.text_called.append((message, default))
            class Text:
                def ask(inner_self):
                    return default or "test"
            return Text()

        def password(self, message, default, validate=None):
            self.password_called.append((message, default))
            class Password:
                def ask(inner_self):
                    return default or "secret"
            return Password()

    mq = MockQuestionary()
    monkeypatch.setattr(prompt, "questionary", mq)
    return mq


def test_scriptfinder_build_tree_basic():
    choices = [
        "dir1/script1.py",
        "dir1/script2.py",
        "dir2/subdir/script3.py",
        "script4.py"
    ]
    sf = prompt.ScriptFinder("Select script", choices)
    root = sf._root
    # Root should have dir1, dir2, script4.py
    assert "dir1" in root.children
    assert "dir2" in root.children
    assert "script4.py" in root.children
    # dir1 should have script1.py and script2.py as scripts
    dir1 = root.children["dir1"]
    assert dir1.children["script1.py"].is_script
    assert dir1.children["script2.py"].is_script
    # dir2 should have subdir
    assert "subdir" in root.children["dir2"].children
    subdir = root.children["dir2"].children["subdir"]
    assert subdir.children["script3.py"].is_script

def test_scriptfinder_add_child_and_node_properties():
    node = prompt._Node("root")
    child = prompt._Node("child", is_script=True)
    node.add_child(child)
    assert "child" in node.children
    assert node.children["child"].is_script

def test_scriptfinder_ask_select_script(monkeypatch):
    # Patch questionary.select to simulate user selecting a script
    choices = [
        "dir/script.py",
        "other.py"
    ]
    sf = prompt.ScriptFinder("Pick script", choices)
    # Simulate user selecting "🐍  other.py"
    def fake_select(message, choices):
        class Select:
            def ask(inner_self):
                # Return the script symbol + separator + name
                for c in choices:
                    if "other.py" in c:
                        return c
                return choices[0]
        return Select()
    monkeypatch.setattr(prompt.questionary, "select", fake_select)
    result = sf.ask()
    assert result == "other.py"

def test_scriptfinder_ask_navigate_dirs(monkeypatch):
    # Simulate user navigating into a directory and selecting a script
    choices = [
        "dir1/script1.py",
        "dir2/script2.py"
    ]
    sf = prompt.ScriptFinder("Pick script", choices)
    call_sequence = []
    def fake_select(message, choices):
        class Select:
            def ask(inner_self):
                # First call: select dir1
                if not call_sequence:
                    call_sequence.append("dir1")
                    for c in choices:
                        if "dir1" in c:
                            return c
                # Second call: select script1.py
                else:
                    for c in choices:
                        if "script1.py" in c:
                            return c
        return Select()
    monkeypatch.setattr(prompt.questionary, "select", fake_select)
    result = sf.ask()
    assert result == "dir1/script1.py"

def test_scriptfinder_script_finder_factory():
    choices = ["a.py", "b.py"]
    sf = prompt.script_finder("Choose", choices)
    assert isinstance(sf, prompt.ScriptFinder)
    assert sf._message == "Choose"
    assert "a.py" in sf._root.children
    assert "b.py" in sf._root.children


def test_resolve_default_env(monkeypatch):
    env = {"FOO": "bar"}
    assert prompt._resolve_default("${FOO}", env) == "bar"
    assert prompt._resolve_default("baz", env) == "baz"
    assert prompt._resolve_default(123, env) == 123


def test_prompt_boolean(mock_questionary):
    result = prompt._prompt_boolean("Are you sure?", default=True)
    assert result is True
    assert mock_questionary.confirm_called


def test_prompt_choices_single(mock_questionary):
    choices = ["a", "b", "c"]
    result = prompt._prompt_choices(
        key="test",
        message="Pick one",
        choices=choices,
        default="a",
        multiple=False,
        validator_func=None,
        required=True
    )
    assert result == "a"
    assert mock_questionary.select_called


def test_prompt_choices_multiple(mock_questionary):
    choices = ["a", "b", "c"]
    # Mark "b" as checked
    result = prompt._prompt_choices(
        key="test",
        message="Pick some",
        choices=choices,
        default=["b"],
        multiple=True,
        validator_func=None,
        required=False
    )
    assert result == ["b"]
    assert mock_questionary.checkbox_called


def test_prompt_path(mock_questionary):
    result = prompt._prompt_path(
        message="Enter path",
        default=Path("/tmp/test.txt"),
        required=True,
        validator_func=None
    )
    assert isinstance(result, Path)
    assert result == Path("/tmp/test.txt")
    assert mock_questionary.path_called


def test_prompt_text_str(mock_questionary):
    result = prompt._prompt_text(
        message="Enter text",
        default="foo",
        secret=False,
        param_type=str,
        required=True,
        validator_func=None
    )
    assert result == "foo"
    assert mock_questionary.text_called


def test_prompt_text_int(mock_questionary):
    result = prompt._prompt_text(
        message="Enter number",
        default="42",
        secret=False,
        param_type=int,
        required=True,
        validator_func=None
    )
    assert result == 42
    assert mock_questionary.text_called


def test_prompt_text_secret(mock_questionary):
    result = prompt._prompt_text(
        message="Enter password",
        default="secret",
        secret=True,
        param_type=str,
        required=True,
        validator_func=None
    )
    assert result == "secret"
    assert mock_questionary.password_called


def test_prompt_for_params_all_types(mock_questionary):
    schema = {
        "flag": {"type": bool, "required": True, "default": True, "description": "A flag"},
        "choice": {"type": str, "choices": ["x", "y"], "default": "x", "description": "Pick one"},
        "multi": {"type": str, "choices": ["a", "b"], "multiple": True, "default": ["b"], "description": "Pick some"},
        "path": {"type": Path, "default": Path("/tmp/test.txt"), "description": "A path"},
        "text": {"type": str, "default": "foo", "description": "Some text"},
        "number": {"type": int, "default": 42, "description": "A number"},
        "secret": {"type": str, "default": "secret", "secret": True, "description": "A secret"},
    }
    env = {}
    result = prompt.prompt_for_params(schema, env)
    assert result["flag"] is True
    assert result["choice"] == "x"
    assert result["multi"] == ["b"]
    assert isinstance(result["path"], Path)
    assert result["text"] == "foo"
    assert result["number"] == 42
    assert result["secret"] == "secret"


def test_prompt_for_params_required(monkeypatch, mock_questionary):
    schema = {
        "required_text": {"type": str, "required": True, "description": "Required text", "default": ""}
    }
    env = {}
    # Simulate empty input by patching the ask method of the Text prompt after creation
    orig_text = mock_questionary.text
    def fake_text(message, default, validate=None):
        text_prompt = orig_text(message, default, validate)
        text_prompt.ask = lambda: ""
        return text_prompt
    monkeypatch.setattr(mock_questionary, "text", fake_text)
    with pytest.raises(ValueError):
        prompt.prompt_for_params(schema, env)


def test_custom_validator(monkeypatch):
    # Test _CustomValidator with a function that returns False and str
    validator = prompt._CustomValidator(lambda x: False)
    class Doc:
        text = "abc"
    with pytest.raises(prompt.ValidationError):
        validator.validate(Doc())

    validator2 = prompt._CustomValidator(lambda x: "error msg")
    with pytest.raises(prompt.ValidationError):
        validator2.validate(Doc())

    validator3 = prompt._CustomValidator(lambda x: True)
    # Should not raise
    validator3.validate(Doc())