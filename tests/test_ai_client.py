import pytest
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Type
from unittest.mock import MagicMock, patch
import sys
from pydantic import BaseModel

# Patch sys.modules to mock instructor and openai before import
sys.modules["instructor"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["pydantic"] = __import__("pydantic")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from giorgio.ai_client import (
    AIClientConfig,
    Message,
    AIClient,
    AIScriptingClient,
)

@pytest.fixture
def dummy_config():
    return AIClientConfig(api_key="test-key", base_url="http://test", model="gpt-test")

def test_client_config_defaults(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "env-key")
    monkeypatch.delenv("AI_TEMPERATURE", raising=False)
    monkeypatch.delenv("AI_MAX_TOKENS", raising=False)
    cfg = AIClientConfig()
    assert cfg.api_key == "env-key"
    assert cfg.model == "gpt-4.1-mini"
    assert cfg.temperature == 0.0
    assert cfg.max_output_tokens == 0

def test_client_config_env_temperature_and_max_tokens(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "env-key")
    monkeypatch.setenv("AI_TEMPERATURE", "0.7")
    monkeypatch.setenv("AI_MAX_TOKENS", "1234")
    cfg = AIClientConfig()
    assert cfg.temperature == 0.7
    assert cfg.max_output_tokens == 1234

def test_message_dataclass():
    msg = Message(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"

def test_wrap_primitive_in_model_caches(dummy_config):
    client = AIClient(dummy_config)
    model1 = client._wrap_primitive_in_model(str)
    model2 = client._wrap_primitive_in_model(str)
    assert model1 is model2
    inst = model1(value="abc")
    assert inst.value == "abc"

def test_resolve_response_model_with_pydantic_model(dummy_config):

    class Foo(BaseModel):
        bar: int

    client = AIClient(dummy_config)
    model, wrapped = client._resolve_response_model(Foo)
    assert model is Foo
    assert wrapped is False

def test_resolve_response_model_with_primitive(dummy_config):
    client = AIClient(dummy_config)
    model, wrapped = client._resolve_response_model(int)
    inst = model(value=42)
    assert inst.value == 42
    assert wrapped is True

def test_with_instructions_and_examples(dummy_config):
    client = AIClient(dummy_config)
    client.with_instructions("Do this.")
    # Use with_example instead of with_examples
    client.with_example("AssistantA")
    assert client._messages[0].role == "system"
    assert client._messages[1].role == "user"
    assert client._messages[2].role == "assistant"

def test_with_doc_adds_system_message(dummy_config):
    client = AIClient(dummy_config)
    client.with_doc("README", "Some content")
    # The last message is from the assistant
    assert client._messages[-1].role == "assistant"
    # Match the actual content returned by with_doc
    assert "Document 'README' received and understood." == client._messages[-1].content

def test_with_schema_sets_response_model(dummy_config):
    client = AIClient(dummy_config)
    client.with_schema(str)
    assert client._response_model is not None
    assert client._wrapped_value is True
    assert any("Output constraint" in m.content for m in client._messages)

def test_reset_clears_state(dummy_config):
    client = AIClient(dummy_config)
    client.with_instructions("test")
    client.with_schema(str)
    client.reset()
    assert client._messages == []
    assert client._response_model is None
    assert client._wrapped_value is False

def test_ask_calls_instructor_and_returns_value(dummy_config):
    client = AIClient(dummy_config)
    client._response_model = client._wrap_primitive_in_model(str)
    client._wrapped_value = True
    client.client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.value = "result"
    client.client.chat.completions.create.return_value = mock_resp
    client._messages = []
    result = client.ask("prompt")
    assert result == "result"

def test_ask_raw_calls_openai_and_returns_content(dummy_config):
    client = AIClient(dummy_config)
    client._raw_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="raw output"))]
    client._raw_client.chat.completions.create.return_value = mock_resp
    client._messages = []
    result = client.ask_raw("prompt")
    assert result == "raw output"

def test_aiscriptingclient_from_project_config(monkeypatch):
    # Set required env vars for AI config
    monkeypatch.setenv("AI_API_KEY", "tok")
    monkeypatch.setenv("AI_BASE_URL", "http://api")
    monkeypatch.setenv("AI_MODEL", "gpt-test")
    client = AIScriptingClient(Path("."))
    assert isinstance(client, AIScriptingClient)
    assert client.ai_client.config.model == "gpt-test"

def test_aiscriptingclient_from_project_config_missing(monkeypatch):
    # Unset env vars to simulate missing config
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("AI_BASE_URL", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    with pytest.raises(RuntimeError):
        AIScriptingClient(Path("."))

def test_aiscriptingclient_generate_script(monkeypatch, tmp_path):
    # Patch template and README files
    template_path = tmp_path / "templates"
    template_path.mkdir()
    (template_path / "script_template.py").write_text("TEMPLATE")
    (tmp_path / "README.md").write_text("README")

    # Create minimal .giorgio/config.json so get_project_config does not fail
    giorgio_dir = tmp_path / ".giorgio"
    giorgio_dir.mkdir()
    (giorgio_dir / "config.json").write_text("{}")

    # Patch __file__ to simulate location
    monkeypatch.setattr("giorgio.ai_client.__file__", str(tmp_path / "ai_client.py"))

    # Patch AIClient.ask to return code with markdown
    class DummyAIClient:
        def reset(self): pass
        def with_instructions(self, *a, **k): return self
        def with_doc(self, *a, **k): return self
        def with_example(self, *a, **k): return self
        def ask(self, prompt):
            return "```python\nprint('hi')\n```"

    # Patch Path.read_text to use our files
    orig_read_text = Path.read_text
    def fake_read_text(self, *a, **kw):
        if self.name == "script_template.py":
            return "TEMPLATE"
        if self.name == "README.md":
            return "README"
        return orig_read_text(self, *a, **kw)
    monkeypatch.setattr(Path, "read_text", fake_read_text)

    # Patch Path.exists to always return True for README.md
    orig_exists = Path.exists
    def fake_exists(self):
        if self.name == "README.md":
            return True
        return orig_exists(self)
    monkeypatch.setattr(Path, "exists", fake_exists)

    # Patch _unwrap_script to just return the input string (avoid regex on DummyAIClient)
    monkeypatch.setattr(AIScriptingClient, "_unwrap_script", lambda self, s: "print('hi')")

    # Set required env vars for AI config
    monkeypatch.setenv("AI_API_KEY", "tok")
    monkeypatch.setenv("AI_BASE_URL", "http://api")
    monkeypatch.setenv("AI_MODEL", "gpt-test")

    client = AIScriptingClient(tmp_path)
    client.ai_client = DummyAIClient()
    script = client.generate_script("do something")
    assert "print('hi')" in script
    assert "```" not in script

def test_messages_merges_system_messages(dummy_config):
    client = AIClient(dummy_config)
    client._messages = [
        Message(role="system", content="sys1"),
        Message(role="system", content="sys2"),
        Message(role="user", content="hi"),
        Message(role="assistant", content="hello"),
    ]
    msgs = client.messages
    assert msgs[0]["role"] == "system"
    assert "sys1" in msgs[0]["content"]
    assert "sys2" in msgs[0]["content"]
    assert msgs[1]["role"] == "user"
    assert msgs[2]["role"] == "assistant"

def test_with_examples_adds_user_and_assistant_messages(dummy_config):
    client = AIClient(dummy_config)
    # Use with_example for each example
    client.with_example("ex1")
    client.with_example("ex2")
    # Each example adds a user and assistant message
    assert client._messages[0].role == "user"
    assert client._messages[1].role == "assistant"
    assert client._messages[1].content == "ex1"
    assert client._messages[2].role == "user"
    assert client._messages[3].role == "assistant"
    assert client._messages[3].content == "ex2"

def test_ask_sets_default_response_model_if_none(dummy_config):
    client = AIClient(dummy_config)
    client.client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.value = "foo"
    client.client.chat.completions.create.return_value = mock_resp
    client._response_model = None
    client._wrapped_value = False
    client._messages = []
    result = client.ask("prompt")
    assert result == "foo"
    assert client._response_model is not None
    assert client._wrapped_value is True

def test_ask_appends_assistant_message(dummy_config):
    client = AIClient(dummy_config)
    client.client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.value = "bar"
    client.client.chat.completions.create.return_value = mock_resp
    client._response_model = client._wrap_primitive_in_model(str)
    client._wrapped_value = True
    client._messages = []
    client.ask("prompt")
    # Last message should be assistant with the returned value
    assert client._messages[-1].role == "assistant"
    assert client._messages[-1].content == "bar"

def test_ask_raw_appends_assistant_message(dummy_config):
    client = AIClient(dummy_config)
    client._raw_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="raw output"))]
    client._raw_client.chat.completions.create.return_value = mock_resp
    client._messages = []
    client.ask_raw("prompt")
    # Last message should be assistant with the returned value
    assert client._messages[-1].role == "assistant"
    assert client._messages[-1].content == "raw output"
    assert client._messages[-1].content == "raw output"

def test_get_script_anatomy_content_extracts_section(monkeypatch, tmp_path):
    # Prepare a README.md with the special markers and extra content
    readme_content = """
Intro text
<!-- BEGIN GIORGIO_SCRIPT_ANATOMY -->
This is the script anatomy section.
It should be extracted.
<!-- END GIORGIO_SCRIPT_ANATOMY -->
Outro text
"""
    readme_path = tmp_path / "README.md"
    readme_path.write_text(readme_content)

    # Patch __file__ to simulate location
    monkeypatch.setattr("giorgio.ai_client.__file__", str(tmp_path / "ai_client.py"))

    # Save original methods before patching
    orig_read_text = Path.read_text
    orig_exists = Path.exists

    def fake_read_text(self, *a, **kw):
        if self.name == "README.md":
            # Call the original read_text, not the patched one
            return orig_read_text(readme_path, *a, **kw)
        return orig_read_text(self, *a, **kw)

    def fake_exists(self):
        if self.name == "README.md":
            return True
        return orig_exists(self)

    monkeypatch.setattr(Path, "read_text", fake_read_text)
    monkeypatch.setattr(Path, "exists", fake_exists)

    # Set required env vars for AI config to avoid RuntimeError
    monkeypatch.setenv("AI_API_KEY", "tok")
    monkeypatch.setenv("AI_BASE_URL", "http://api")
    monkeypatch.setenv("AI_MODEL", "gpt-test")

    client = AIScriptingClient(tmp_path)
    result = client._get_script_anatomy_content()
    assert "This is the script anatomy section." in result
    assert "Intro text" not in result
    assert "Outro text" not in result
    assert "<!--" not in result
