import ast
from typing import Dict, Any, List, Callable, Union, Optional
from pathlib import Path

import questionary
from questionary import Choice, Validator, ValidationError


class _Node:
    """
    Represents a node in a hierarchical tree structure, which can be either a
    directory or a script.

    :param name: The name of the node.
    :type name: str
    :param is_script: Indicates whether the node represents a script (True) or a
    directory (False).
    :type is_script: bool
    """

    def __init__(self, name: str, is_script: bool = False) -> None:
        self.name = name
        self.is_script = is_script
        self.children: Dict[str, _Node] = {}

    def add_child(self, child: "_Node") -> None:
        """
        Adds a child node to the current node.
        
        :param child: The child node to be added. Must be an instance of _Node.
        :type child: _Node
        :return: None
        :rtype: None
        """

        self.children[child.name] = child


class ScriptFinder:
    """
    Interactive prompt for navigating and selecting script paths from a list of
    slash-delimited choices.
    This class builds a tree structure from the provided choices and allows the
    user to interactively
    traverse directories and select scripts using a menu-based interface.
    
    :param message: The prompt message displayed to the user.
    :type message: str
    :param choices: List of slash-delimited script paths.
    :type choices: List[str]
    """

    dir_symbol = "📁"
    script_symbol = "🐍"
    back_symbol = "⬅️"
    choice_separator = "  "

    def __init__(
        self,
        message: str,
        choices: List[str],
        scripts_dir: str = "scripts"
    ) -> None:
        self._message = message
        self._root = self._build_tree(choices)
        self._scripts_dir = scripts_dir

    @staticmethod
    def _build_tree(choices: List[str]) -> _Node:
        """
        Builds a tree structure from the provided slash-delimited choices.
        Each choice is split by slashes to create a hierarchy of directories and
        scripts.

        :param choices: List of slash-delimited script paths.
        :type choices: List[str]
        :return: The root node of the tree structure.
        :rtype: _Node
        """

        root = _Node(name="", is_script=False)

        for path in choices:
            parts = path.strip("/").split("/")
            current = root

            for index, part in enumerate(parts):
                is_script = index == len(parts) - 1

                if part not in current.children:
                    current.children[part] = _Node(name=part, is_script=is_script)

                else:
                    # If existing node becomes a script
                    if is_script:
                        current.children[part].is_script = True

                current = current.children[part]

        return root

    @staticmethod
    def _get_script_name(script_path: str, scripts_dir: str) -> str:
        """
        Retrieves the name of a script from its configuration or falls back to
        the folder name. Uses AST to extract CONFIG["name"] without executing the module.
        
        :param script_path: Relative path to the script folder.
        :type script_path: str
        :param scripts_dir: Base directory containing script folders.
        :type scripts_dir: str
        :return: The name of the script as specified in its configuration, or
        the folder name if not found.
        :rtype: str
        """
        
        full_path = Path(scripts_dir) / script_path / "script.py"
        
        if not full_path.is_file():
            return script_path  # fallback
        
        try:
            # Read the file content
            with open(full_path, "r", encoding="utf-8") as f:
                file_content = f.read()
            
            # Parse the content with AST
            tree = ast.parse(file_content)
            
            # Look for CONFIG assignment and extract CONFIG["name"] if present
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "CONFIG" for t in node.targets)
                    and isinstance(node.value, ast.Dict)
                ):
                    for key, value in zip(node.value.keys, node.value.values):
                        if (
                            isinstance(key, ast.Constant) and key.value == "name"
                            and isinstance(value, ast.Constant)
                        ):
                            return value.value
            
        except Exception:
            # In case of error, use the fallback
            pass
        
        # Fallback: return the parent folder name
        return script_path
    
    def _build_dir_choice(self, name: str) -> Choice:
        """
        Creates a Choice object for a directory node.

        :param name: The name of the directory.
        :type name: str
        :return: A Choice object representing the directory.
        :rtype: Choice
        """
        
        name_display = name.replace("_", " ").capitalize()
        title = f"{self.dir_symbol}{self.choice_separator}{name_display}"
        value = ("__dir__", name)

        return Choice(title=title, value=value)
    
    def _build_script_choice(self, path: str) -> Choice:
        """
        Creates a Choice object for a script node.

        :param path: The relative path to the script.
        :type path: str
        :return: A Choice object representing the script.
        :rtype: Choice
        """
        
        title = (
            f"{self.script_symbol}{self.choice_separator}"
            f"{self._get_script_name(path, self._scripts_dir)}"
        )
        value = path

        return Choice(title=title, value=value)

    def ask(self) -> Optional[str]:
        """
        Displays an interactive menu for the user to select a script path.
        The user can navigate through directories and select a script. If the
        user selects a directory, they can navigate deeper into the tree.
        If the user selects a script, the full path is returned.
        If the user chooses to go back, they can return to the previous
        directory.

        :return: The selected script path as a slash-delimited string, or None
        if the user cancels the selection.
        :rtype: Optional[str]
        """

        current = self._root
        stack: List[_Node] = []
        path_parts: List[str] = []

        choice_separator = self.choice_separator
        back_symbol = self.back_symbol
        back_choice = f"{back_symbol}{choice_separator}.."

        while True:
            menu_items: List[Any] = []

            if stack:
                menu_items.append(Choice(title=back_choice, value="__back__"))

            dirs = sorted([
                name
                for name, node in current.children.items()
                if not node.is_script
            ])

            scripts = sorted([
                name
                for name, node in current.children.items()
                if node.is_script
            ])

            menu_items += [
                self._build_dir_choice(d)
                for d in dirs
            ]
            
            # For each script, build a choice with the full path for value and name lookup
            # Create full paths for scripts by prepending the current directory path
            menu_items += [
                self._build_script_choice_with_path(s, path_parts)
                for s in scripts
            ]

            prompt = self._message
            if len(path_parts):
                prompt += f" ({'/'.join(path_parts)}/)"

            choice = questionary.select(prompt, choices=menu_items).ask()
            if choice is None:
                return None

            if choice == "__back__":
                current = stack.pop()
                path_parts.pop()
                continue

            if isinstance(choice, tuple) and choice[0] == "__dir__":
                # It's a directory, navigate into it
                stack.append(current)
                current = current.children[choice[1]]
                path_parts.append(choice[1])
                continue

            # Otherwise, it's a script, return the path
            return choice
            
    def _build_script_choice_with_path(self, script_name: str, path_parts: List[str]) -> Choice:
        """
        Creates a Choice object for a script node with the correct full path.
        
        :param script_name: The name of the script file/directory.
        :type script_name: str
        :param path_parts: The current directory path parts.
        :type path_parts: List[str]
        :return: A Choice object representing the script with full path.
        :rtype: Choice
        """
        # Construct the full path by joining the current directory path with the script name
        full_path = "/".join(path_parts + [script_name]) if path_parts else script_name
        
        # Get the user-friendly name using the full path
        user_name = self._get_script_name(full_path, self._scripts_dir)
        
        title = f"{self.script_symbol}{self.choice_separator}{user_name}"
        
        # The value must be the full path for proper script execution
        return Choice(title=title, value=full_path)

def script_finder(
    message: str,
    choices: List[str],
    scripts_dir: str = "scripts"
) -> ScriptFinder:
    """
    Creates an instance of ScriptFinder to interactively select a script path
    from a list of slash-delimited choices.

    :param message: The prompt message displayed to the user.
    :type message: str
    :param choices: List of slash-delimited script paths.
    :type choices: List[str]
    :param scripts_dir: The directory where scripts are located, used for
    resolving script names.
    :type scripts_dir: str
    :return: An instance of ScriptFinder.
    :rtype: ScriptFinder
    """

    return ScriptFinder(message, choices, scripts_dir)


class _CustomValidator(Validator):
    """
    Wraps a validator function returning bool or str into questionary.Validator.

    :param func: A callable that takes any input and returns either a boolean or
    a string.
    :type func: Callable[[Any], Union[bool, str]]
    """

    def __init__(self, func: Callable[[Any], Union[bool, str]]):
        self.func = func

    def validate(self, document):
        """
        Validates the input document using the provided function.

        :param document: The input document to validate.
        :type document: questionary.document.Document
        :return: None
        :rtype: None
        :raises ValidationError: If the validation fails, raises a
        ValidationError with an appropriate message and cursor position.
        """

        text = document.text

        try:
            result = self.func(text)

        except Exception as e:
            raise ValidationError(message=str(e), cursor_position=len(text))
        
        if result is False:
            raise ValidationError(message="Invalid value", cursor_position=len(text))
        
        if isinstance(result, str):
            raise ValidationError(message=result, cursor_position=len(text))


def _resolve_default(default: Any, env: Dict[str, str]) -> Any:
    """
    If default is a "${VAR}" string, replace it by env[VAR].
    Otherwise return default unchanged.

    :param default: The default value which may be a string in the format "${VAR}".
    :type default: Any
    :param env: A dictionary containing environment variables.
    :type env: Dict[str, str]
    :return: The resolved default value.
    :rtype: Any
    """
    
    if isinstance(default, str) and default.startswith("${") and default.endswith("}"):
        var = default[2:-1]
        return env.get(var)
    
    return default


def _prompt_boolean(
    message: str, default: Optional[bool]
) -> bool:
    """
    Prompt for a boolean value using questionary.confirm.

    :param message: The message to display in the prompt.
    :type message: str
    :param default: The default value for the boolean prompt.
    :type default: Optional[bool]
    :return: The boolean value entered by the user.
    :rtype: bool
    """
    
    return questionary.confirm(
        message=message,
        default=bool(default) if default is not None else False
    ).ask()


def _prompt_choices(
    key: str,
    message: str,
    choices: List[Any],
    default: Any,
    multiple: bool,
    validator_func: Optional[Callable[[Any], Union[bool, str]]],
    required: bool = False
) -> Union[Any, List[Any]]:
    """
    Prompt for a choice or multiple choices using questionary.select or
    questionary.checkbox.

    :param key: The parameter key for error messages.
    :type key: str
    :param message: The message to display in the prompt.
    :type message: str
    :param choices: A list of choices to present to the user.
    :type choices: List[Any]
    :param default: The default choice or choices.
    :type default: Any
    :param multiple: Whether to allow multiple choices.
    :type multiple: bool
    :param validator_func: An optional custom validator function that takes the
    selected value(s) and returns True if valid, False or a
    string error message if invalid.
    :type validator_func: Optional[Callable[[Any], Union[bool, str]]]
    :param required: Whether the choice is required.
    :type required: bool
    :return: The selected choice or choices.
    :rtype: Union[Any, List[Any]]
    :raises ValueError: If a required choice is not provided.
    """

    qchoices = [
        Choice(
            title=str(c),
            value=c,
            checked=(default is not None and c in default) if multiple else None
        )
        for c in choices
    ]
    
    validator = _CustomValidator(validator_func) if validator_func else lambda _: True

    if multiple:
        answer = questionary.checkbox(
            message=message,
            choices=qchoices,
            validate=validator
        ).ask()
        
        if answer is None:
            return []
        
        return answer

    else:
        default_choice = default if default in choices else None

        # Loop until the validator_func (if any) accepts the choice
        while True:
            answer = questionary.select(
                message=message,
                choices=qchoices,
                default=default_choice
            ).ask()

            # If no custom validator, accept immediately
            if not validator_func:
                break

            # Run your custom validator on the selected value
            result = validator_func(answer)
            
            if result is False:
                print(f"Validation failed for '{key}'. Please choose again.")
                continue
            
            if isinstance(result, str):
                print(f"{result}  Please choose again.")
                continue

            # Passed validation
            break

        if required and answer is None:
            raise ValueError(f"Parameter '{key}' is required.")
        
        return answer


def _prompt_path(
    message: str,
    default: Optional[Path],
    required: bool = False,
    validator_func: Optional[Callable[[Path], Union[bool, str]]] = None
) -> Path:
    """
    Prompt for a file or directory path using questionary.path.

    :param message: The message to display in the prompt.
    :type message: str
    :param default: The default path to use if the user does not provide input.
    :type default: Optional[Path]
    :param required: Whether the input is required.
    :type required: bool
    :param validator_func: An optional custom validator function that takes the
    input value and returns True if valid, False or a string error message if
    invalid.
    :type validator_func: Optional[Callable[[Path], Union[bool, str]]]
    :return: The validated Path object.
    :rtype: Path
    """
    
    def path_validator(text: str) -> Union[bool, str]:
        """
        Validate the input text as a file or directory path.

        :param text: The input text to validate.
        :type text: str
        :return: True if valid, False or a string error message if invalid.
        :rtype: Union[bool, str]
        """
        if text == "":
            if required and default is None:
                return "This field is required."
            return True
        
        path = Path(text)
        
        if validator_func:
            valid = validator_func(path)
            if valid is False:
                return "Validation failed."
            if isinstance(valid, str):
                return valid
        
        return True

    validator = _CustomValidator(path_validator)

    answer = questionary.path(
        message=message,
        default=str(default) if default else "",
        validate=validator
    ).ask()

    if answer == "":
        return default
    
    return Path(answer)


def _prompt_text(
    message: str,
    default: str,
    secret: bool,
    param_type: type,
    required: bool,
    validator_func: Optional[Callable[[Any], Union[bool, str]]]
) -> Any:
    """
    Prompt for text, int or float. Uses questionary.password for secret,
    questionary.text otherwise, with a custom validator that handles type
    conversion.

    :param message: The message to display in the prompt.
    :type message: str
    :param default: The default value to use if the user does not provide input.
    :type default: str
    :param secret: Whether the input should be hidden (for passwords).
    :type secret: bool
    :param param_type: The type to convert the input to (e.g., str, int, float).
    :type param_type: type
    :param required: Whether the input is required.
    :type required: bool
    :param validator_func: An optional custom validator function that takes the
    input value and returns True if valid, False or a string error message if
    invalid.
    :type validator_func: Optional[Callable[[Any], Union[bool, str]]]
    :return: The converted input value.
    :rtype: Any
    """
    validator: Optional[Validator] = None

    def type_validator(text: str) -> Union[bool, str]:
        """
        Validate the input text by converting it to the specified type and
        applying the custom validator function if provided.

        :param text: The input text to validate.
        :type text: str
        :return: True if valid, False or a string error message if invalid.
        :rtype: Union[bool, str]
        :raises ValueError: If the input cannot be converted to the specified type.
        """
        if text == "":
            if required and default is None:
                return "This field is required."
            
            return True
        
        try:
            val = param_type(text)
        
        except ValueError:
            return f"Please enter a valid {param_type.__name__}."
        
        if validator_func:
            valid = validator_func(val)

            if valid is False:
                return "Validation failed."
            
            if isinstance(valid, str):
                return valid
        
        return True

    validator = _CustomValidator(type_validator)

    if secret:
        answer = questionary.password(
            message=message,
            default=str(default) if default is not None else "",
            validate=validator
        ).ask()
        
    else:
        answer = questionary.text(
            message=message,
            default=str(default) if default is not None else "",
            validate=validator
        ).ask()

    if answer == "":
        return default
    
    return param_type(answer) if param_type in (int, float) else answer


def prompt_for_params(
    schema: Dict[str, Dict[str, Any]],
    env: Dict[str, str]
) -> Dict[str, Any]:
    """
    Prompt the user for parameters defined in the schema using questionary.

    :param schema: A dictionary defining the parameters to prompt for, where each
    key is the parameter name and the value is a dictionary with metadata such
    as type, required, default, choices, description, secret, validator, and
    multiple.
    :type schema: Dict[str, Dict[str, Any]]
    :param env: A dictionary containing environment variables to resolve defaults.
    :type env: Dict[str, str]
    :return: A dictionary containing the collected parameters.
    :rtype: Dict[str, Any]
    :raises ValueError: If a required parameter is not provided or validation fails.
    """
    collected: Dict[str, Any] = {}

    for key, meta in schema.items():
        param_type = meta.get("type", str)
        required = meta.get("required", False)
        default = _resolve_default(meta.get("default"), env)
        choices = meta.get("choices")
        description = meta.get("description", key)
        secret = meta.get("secret", False)
        validator_func = meta.get("validator")
        multiple = meta.get("multiple", False)

        # Build message
        message = f"{description} ({key})"

        if choices:
            message += f" [choices: {', '.join(map(str, choices))}]"

        if default is not None:
            message += f" [default: {default}]"

        # Dispatch
        if param_type is bool and not choices:
            value = _prompt_boolean(message, default)

        elif choices:
            value = _prompt_choices(
                key, message, choices, default,
                multiple, validator_func, required
            )

        elif param_type is Path:
            value = _prompt_path(
                message, default, required, validator_func
            )

        else:
            value = _prompt_text(
                message, str(default) if default is not None else "",
                secret, param_type, required, validator_func
            )

            value = param_type(value)

        # Final required check
        if required and (value is None or (isinstance(value, str) and value == "")):
            raise ValueError(f"Parameter '{key}' is required but was not provided.")

        collected[key] = value

    return collected
