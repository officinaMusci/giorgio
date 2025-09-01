from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union
)

import instructor
from openai import OpenAI
from pydantic import BaseModel, create_model, Field

from .project_manager import get_project_config

# Cache for wrapping primitive/composite types into Pydantic models
_MODEL_CACHE: Dict[Any, Type[BaseModel]] = {}

MessageRole = Literal["system", "user", "assistant", "tool"]
T = TypeVar("T")


@dataclass
class ClientConfig:
    """Configuration settings for the OpenAI backend via Instructor."""
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    base_url: Optional[str] = None
    model: str = "gpt-4.1-mini"
    temperature: float = 0.0
    request_timeout: Optional[float] = 60.0
    max_output_tokens: Optional[int] = None
    instructor_mode: instructor.Mode = instructor.Mode.JSON
    max_retries: int = 2


@dataclass
class Message:
    """A single chat message with a role and content."""
    role: MessageRole
    content: str


class AIClient(Generic[T]):
    """
    High-level AI client using Instructor + Pydantic for typed prompts.
    """
    
    def __init__(self, config: ClientConfig) -> None:
        """
        Initialize the AIClient with configuration and raw OpenAI client.

        :param config: Settings for API key, model, retries, etc.
        :type config: ClientConfig
        :returns: None
        :rtype: None
        """
        self.config = config

        # Prepare kwargs for low-level OpenAI client
        base_kwargs: Dict[str, Any] = {}
        if config.base_url:
            base_kwargs["base_url"] = config.base_url
        if config.api_key:
            base_kwargs["api_key"] = config.api_key

        # Instantiate the raw OpenAI client
        self._raw_client = OpenAI(**{k: v for k, v in vars(config).items() if k in ("api_key", "base_url") and v})

        # Wrap raw client with Instructor to enforce JSON schema & retries
        self.client = instructor.from_openai(
            self._raw_client,
            mode=config.instructor_mode,
        )

        # Initialize per-call state
        self._messages: List[Message] = []
        self._response_model: Optional[Type[BaseModel]] = None
        self._wrapped_value = False

    def _wrap_primitive_in_model(self, py_type: Any) -> Type[BaseModel]:
        """
        Build and cache a Pydantic model wrapping a primitive or typing type.

        :param py_type: A Python builtin or typing hint to wrap.
        :type py_type: Any
        :returns: A Pydantic model class with a single `value` field.
        :rtype: Type[BaseModel]
        """
        if py_type in _MODEL_CACHE:
            return _MODEL_CACHE[py_type]

        model = create_model(
            "Value",
            value=(py_type, Field(..., description="Return the result in this field named 'value'")),
            __base__=BaseModel,
        )
        _MODEL_CACHE[py_type] = model
        return model


    def _resolve_response_model(self, target: Union[Type[T], Any]) -> Tuple[Type[BaseModel], bool]:
        """
        Select or wrap a response type into a Pydantic model for validation.

        :param target: Either a BaseModel subclass or a Python/typing hint.
        :type target: Union[Type[T], Any]
        :returns: The model to use and a flag indicating whether it was wrapped.
        :rtype: Tuple[Type[BaseModel], bool]
        """
        is_model = isinstance(target, type) and issubclass(target, BaseModel)
        if is_model:
            return target, False  # already a Pydantic model

        wrapped = self._wrap_primitive_in_model(target)
        return wrapped, True

    def with_instructions(self, text: str) -> "AIClient[T]":
        """
        Add system instructions guiding the AI’s overall behavior.

        :param text: Instructional text to prepend as a system message.
        :type text: str
        :returns: Self, for method chaining.
        :rtype: AIClient[T]
        """
        self._messages.append(Message(role="system", content=text))
        return self

    def with_examples(self, pairs: Iterable[Tuple[str, str]]) -> "AIClient[T]":
        """
        Include example user→assistant exchanges to shape formatting.

        :param pairs: List of (user, assistant) example pairs.
        :type pairs: Iterable[Tuple[str, str]]
        :returns: Self, for method chaining.
        :rtype: AIClient[T]
        """
        for user_text, assistant_text in pairs:
            self._messages.append(Message(role="user", content=user_text))
            self._messages.append(Message(role="assistant", content=assistant_text))
        return self

    def with_doc(
        self,
        name: str,
        content: str,
        strategy: Literal["full", "summary", "chunk"] = "summary",
    ) -> "AIClient[T]":
        """
        Attach a named context document to the prompt.

        :param name: Identifier for the document (e.g., "README").
        :type name: str
        :param content: Raw text of the document.
        :type content: str
        :param strategy: How to present the doc ("full", "summary", "chunk").
        :type strategy: Literal["full", "summary", "chunk"]
        :returns: Self, for method chaining.
        :rtype: AIClient[T]
        """
        tagged = f"Context document [{name}]:\n{content}"
        self._messages.append(Message(role="system", content=tagged))
        return self

    def with_schema(self, type_hint: Union[Type[T], Any], json_only: bool = True) -> "AIClient[T]":
        """
        Define the expected response schema or native type.

        :param type_hint: A BaseModel subclass or typing hint.
        :type type_hint: Union[Type[T], Any]
        :param json_only: If True, enforce pure JSON output.
        :type json_only: bool
        :returns: Self, for method chaining.
        :rtype: AIClient[T]
        """
        model, wrapped = self._resolve_response_model(type_hint)
        self._response_model, self._wrapped_value = model, wrapped

        fmt = (
            "You MUST return ONLY valid JSON. No text outside the JSON."
            if json_only
            else "Your output MUST strictly conform to the expected schema."
        )
        self._messages.append(Message(role="system", content=f"Output constraint: {fmt}"))
        return self

    def ask(self, prompt: str) -> T:
        """
        Send the prompt to the AI, enforce schema, and return a typed result.

        :param prompt: The final user input to append before calling the API.
        :type prompt: str
        :returns: The validated and typed response.
        :rtype: T
        :raises ValueError: If no schema was set prior to calling `ask`.
        """
        if self._response_model is None:
            raise ValueError("No schema specified. Call `with_schema(...)` before `ask(...)`.")

        self._messages.append(Message(role="user", content=prompt))
        messages = [{"role": m.role, "content": m.content} for m in self._messages]

        # Perform chat completion with schema enforcement and retries
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            response_model=self._response_model,
            max_retries=self.config.max_retries,
        )

        return response.value if self._wrapped_value else response  # type: ignore

    def reset(self) -> None:
        """
        Clear accumulated messages and schema settings for a fresh session.

        :returns: None
        :rtype: None
        """
        self._messages.clear()
        self._response_model = None
        self._wrapped_value = False

    def ask_raw(self, prompt: str) -> str:
        """Send the prompt to the AI and return raw assistant text (no JSON)."""
        self._messages.append(Message(role="user", content=prompt))
        messages = [{"role": m.role, "content": m.content} for m in self._messages]
        response = self._raw_client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            timeout=self.config.request_timeout,
        )
        return response.choices[0].message.content  # type: ignore


class AIScriptingClient:
    """
    Minimal client to generate Python automation scripts based on project
    context and AI instructions.
    """

    role_description = """
You are a seasoned Python developer, attentive to best practices and coding standards—especially PEP 8. Your code (in English only) must be:

- Readable and well-documented (with docstrings where appropriate)
- Modular, following DRY, KISS, and SRP principles.
    """

    mission_description = """
Your mission is to generate a valid Giorgio automation script:
- Your output MUST strictly follow the structure and standards shown in the script_template.py example and the README documentation.
- Use the script_template.py as a skeleton for your output.
- Do NOT output anything except the code itself, and do NOT add any extra text, comments, or explanations outside the code.
- The script must include CONFIG, PARAMS, and a run(context) function as shown in the template.
"""

    def __init__(self, api_url: str, model: str, api_key: str = None):
        """
        Initialize the scripting client with API endpoint, model, and key.

        :param api_url: Base URL of the AI service.
        :type api_url: str
        :param model: Name of the AI model to use.
        :type model: str
        :param api_key: Service authentication token.
        :type api_key: str, optional
        :returns: None
        :rtype: None
        """
        cfg = ClientConfig(api_key=api_key, base_url=api_url, model=model)
        self.ai_client = AIClient(cfg)

    @classmethod
    def from_project_config(cls, project_root: Path):
        """
        Load AI config from .giorgio/config.json and build a client.

        :param project_root: Root directory of the project.
        :type project_root: Path
        :returns: Instantiated AIScriptingClient.
        :rtype: AIScriptingClient
        :raises RuntimeError: If required AI config fields are missing.
        """
        config = get_project_config(project_root)

        ai_cfg = config.get("ai", {})
        api_url = ai_cfg.get("url")
        model = ai_cfg.get("model")
        api_key = ai_cfg.get("token")

        if not (api_url and model):
            raise RuntimeError(
                "AI config missing in .giorgio/config.json (need 'ai': { 'url', 'model', ... })"
            )
        
        client = cls(api_url, model, api_key)
        return client

    def generate_script(self, instructions: str) -> str:
        """
        Generate a Python automation script based on instructions and context.

        :param instructions: User-provided instructions for the script.
        :type instructions: str
        :returns: Generated Python script.
        :rtype: str
        """
        self.ai_client.reset()

        # Load example template and project README
        template_path = Path(__file__).parent / "templates" / "script_template.py"
        template_example = template_path.read_text().strip()

        readme_path = Path(__file__).parent.parent / "README.md"
        readme_text = readme_path.read_text().strip()

        # Build prompt and fetch raw Python code
        client = self.ai_client
        client.reset()
        
        script = (
            client
                .with_instructions(
                    f"""{self.role_description.strip()}\n\n{self.mission_description.strip()}"""
                )
                .with_doc("README", readme_text)
                .with_examples([
                    ("Show me an example Giorgio script.", template_example)
                ])
                .ask_raw(instructions)
        )

        # Clean up any markdown fences that might have been returned
        script = self._clean_markdown(script)
        return script
        
    def _clean_markdown(self, text: str) -> str:
        """
        Remove markdown code blocks, language identifiers, and other formatting.

        :param text: Input text to clean.
        :type text: str
        :returns: Cleaned text without markdown formatting.
        :rtype: str
        """
        text = text.strip()

        # Remove triple-quoted blocks
        if text.startswith('"""') and text.endswith('"""'):
            text = text[3:-3].strip()
        elif text.startswith("'''") and text.endswith("'''"):
            text = text[3:-3].strip()

        # Remove markdown code blocks (``` or ```python)
        if text.startswith("```"):
            lines = text.splitlines()
            # Remove the first line (``` or ```python)
            if len(lines) > 1 and lines[0].strip().startswith("```"):
                lines = lines[1:]
            # Remove the last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            # Remove a language identifier if present
            if lines and lines[0].strip().lower() in ("python", "py"):
                lines = lines[1:]
            text = "\n".join(lines).strip()

        # Remove any stray backticks or triple quotes
        text = text.replace("`", "").replace('"""', "").replace("'''", "")

        return text