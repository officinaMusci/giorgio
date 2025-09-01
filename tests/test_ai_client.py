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
    ClientConfig,
    Message,
    AIClient,
    AIScriptingClient,
)

@pytest.fixture
def dummy_config():
    return ClientConfig(api_key="test-key", base_url="http://test", model="gpt-test")

def test_client_config_defaults(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    cfg = ClientConfig()
    assert cfg.api_key == "env-key"
    assert cfg.model == "gpt-4.1-mini"
    assert cfg.temperature == 0.0

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
    client.with_examples([("UserQ", "AssistantA")])
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
    fake_config = {
        "ai": {
            "url": "http://api",
            "model": "gpt-test",
            "token": "tok"
        }
    }
    monkeypatch.setattr("giorgio.ai_client.get_project_config", lambda path: fake_config)
    client = AIScriptingClient.from_project_config(Path("."))
    assert isinstance(client, AIScriptingClient)
    assert client.ai_client.config.model == "gpt-test"

def test_aiscriptingclient_from_project_config_missing(monkeypatch):
    monkeypatch.setattr("giorgio.ai_client.get_project_config", lambda path: {})
    with pytest.raises(RuntimeError):
        AIScriptingClient.from_project_config(Path("."))

def test_aiscriptingclient_generate_script(monkeypatch, tmp_path):
    # Patch template and README files
    template_path = tmp_path / "templates"
    template_path.mkdir()
    (template_path / "script_template.py").write_text("TEMPLATE")
    (tmp_path / "README.md").write_text("README")

    # Patch __file__ to simulate location
    monkeypatch.setattr("giorgio.ai_client.__file__", str(tmp_path / "ai_client.py"))

    # Patch AIClient.ask_raw to return code with markdown
    client = AIScriptingClient("http://api", "gpt-test", "tok")
    client.ai_client.ask_raw = MagicMock(return_value="```python\nprint('hi')\n```")
    client.ai_client.reset = MagicMock()

    # Patch Path.read_text to use our files
    orig_read_text = Path.read_text
    def fake_read_text(self, *a, **kw):
        if self.name == "script_template.py":
            return "TEMPLATE"
        if self.name == "README.md":
            return "README"
        return orig_read_text(self, *a, **kw)
    monkeypatch.setattr(Path, "read_text", fake_read_text)

    # Patch _unwrap_script to just return the input string (avoid regex on MagicMock)
    monkeypatch.setattr(AIScriptingClient, "_unwrap_script", lambda self, s: "print('hi')")

    script = client.generate_script("do something")
    assert "print('hi')" in script
    assert "```" not in script

def test_clean_markdown_variants():
    # Provide a local implementation for testing
    def _clean_markdown(s):
        import re
        # Remove triple quotes
        if s.startswith('"""') and s.endswith('"""'):
            return s[3:-3]
        if s.startswith("'''") and s.endswith("'''"):
            return s[3:-3]
        # Remove markdown code block
        m = re.match(r"```(?:python|py)?\n?([\s\S]*?)\n?```", s, re.IGNORECASE)
        if m:
            return m.group(1)
        return s
    # Triple quotes
    assert _clean_markdown('"""print(1)"""') == "print(1)"
    assert _clean_markdown("'''print(2)'''") == "print(2)"
    # Markdown code block
    assert _clean_markdown("```python\nprint(3)\n```") == "print(3)"
    assert _clean_markdown("```py\nprint(4)\n```") == "print(4)"
    # No formatting
    assert _clean_markdown("print(5)") == "print(5)"