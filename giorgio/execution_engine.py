import os
import sys
import importlib.util
from pathlib import Path
import signal
import logging
from types import MappingProxyType
from typing import Any, Dict, Optional, Callable, List

from .prompt import prompt_for_params
from .project_manager import get_project_config

class GiorgioCancellationError(Exception):
    """
    Raised when the user requests cancellation (e.g. via Ctrl+C)
    during script execution.
    """
    pass


class Context:
    """
    Manages execution context for scripts, including parameters, environment
    variables, and interaction with the execution engine.
    """

    def __init__(
        self,
        initial_params: Dict[str, Any],
        env: Dict[str, str],
        add_params_callback: Optional[Callable[[Dict[str, Dict[str, Any]], Dict[str, str]], Dict[str, Any]]],
        engine: "ExecutionEngine",
    ):
        """
        Initialize the object with the given parameters, environment, callback,
        and engine.
        
        :param initial_params: Initial parameters for the execution engine.
        :type initial_params: Dict[str, Any]
        :param env: Environment variables to be used.
        :type env: Dict[str, str]
        :param add_params_callback: Optional callback to add or modify
        parameters. Should accept a dictionary of parameters and environment,
        and return a dictionary of additional parameters.
        :type add_params_callback: Optional[Callable[[Dict[str, Dict[str, Any]], Dict[str, str]], Dict[str, Any]]]
        :param engine: Reference to the execution engine instance.
        :type engine: ExecutionEngine
        """

        self._params = initial_params.copy()
        self.params = MappingProxyType(self._params)
        self.env = env.copy()
        self._add_params_callback = add_params_callback
        self._engine = engine
        # Provide a logger for scripts via context.logger. Default to the
        # top-level 'giorgio' logger; callers may override to a script-specific
        # child logger before running the script.
        self.logger = logging.getLogger("giorgio")

    def add_params(self, schema: Dict[str, Dict[str, Any]]) -> None:
        """
        Request additional parameters interactively based on the provided schema.

        :param schema: A dictionary defining the parameters to request, where
        keys are parameter names and values are dictionaries
        containing metadata like type, default value, choices, etc.
        :type schema: Dict[str, Dict[str, Any]]
        :returns: None
        :rtype: None
        :raises RuntimeError: If called in non-interactive mode without a
        callback.
        :raises KeyError: If a parameter with the same name already exists.
        :raises Exception: If any other error occurs during parameter addition.
        """

        if not self._add_params_callback:
            raise RuntimeError("Cannot request additional parameters in non-interactive mode.")
        
        new_values = self._add_params_callback(schema, self.env)
        
        for key, value in new_values.items():
            if key in self._params:
                raise KeyError(f"Parameter '{key}' already exists.")
            
            self._params[key] = value

    def call_script(self, script_path: str, args: Optional[Dict[str, Any]] = None) -> None:
        self._engine.run_script(
            script_path,
            cli_args=args or {},
            add_params_callback=self._add_params_callback,
        )


class ExecutionEngine:
    """
    The ExecutionEngine class is responsible for running user-defined scripts
    within a Giorgio project. It manages the execution context, including
    parameters, environment variables, and script imports.
    """

    def __init__(self, project_root: Path):
        """
        Initialize the ExecutionEngine with the project root directory.

        :param project_root: The root directory of the Giorgio project.
        :type project_root: Path
        """
        
        self.project_root = project_root
        self.env = self._load_env()
        self.module_paths = self._load_module_paths()

    def _load_env(self) -> Dict[str, str]:
        """
        Load environment variables from the .env file in the project root.

        :returns: A dictionary of environment variables loaded from the .env
        file.
        :rtype: Dict[str, str]
        :raises RuntimeError: If python-dotenv is not installed and .env file
        exists.
        :raises FileNotFoundError: If the .env file does not exist.
        """

        env_file = self.project_root / ".env"
        
        if env_file.exists():
            try:
                from dotenv import load_dotenv

            except ImportError:
                raise RuntimeError("python-dotenv is required to load .env files.")
            
            load_dotenv(dotenv_path=str(env_file), override=False)

        return dict(os.environ)

    def _load_module_paths(self):
        """
        Load module paths from project config using get_project_config.
        Returns a list of absolute paths.
        """
        try:
            config = get_project_config(self.project_root)
        except Exception:
            return []
        
        module_paths: List[str] = config.get("module_paths", [])
        abs_paths = []
        
        for p in module_paths:
            abs_paths.append(str((self.project_root / p).resolve()))
        
        return abs_paths

    def _import_script_module(self, script: str):
        """
        Import a script module from the scripts directory.

        :param script: The path to the script relative to the scripts directory,
        using forward slashes (e.g., "my_script/script.py").
        :type script: str
        :returns: The imported module.
        :rtype: ModuleType
        :raises FileNotFoundError: If the script file does not exist.
        """

        scripts_dir = self.project_root / "scripts"
        module_path = scripts_dir / script / "script.py"
        if not module_path.exists():
            raise FileNotFoundError(f"Script '{script}' not found under scripts/.")

        # Prepare sys.path insertions
        project_root_str = str(self.project_root.resolve())
        mod_paths = [str(Path(p).resolve()) for p in self.module_paths]
        paths_to_insert = [project_root_str] + mod_paths + [str(scripts_dir)]
        inserted = []

        # Insert paths if not already present
        for p in reversed(paths_to_insert):
            if p not in sys.path:
                sys.path.insert(0, p)
                inserted.append(p)

        # Ensure each module path is a package
        for mod_path in mod_paths:
            mod_dir = Path(mod_path)
            if not mod_dir.exists():
                raise RuntimeError(f"Module path '{mod_path}' does not exist.")
            init_py = mod_dir / "__init__.py"
            if not init_py.exists():
                init_py.touch()

        try:
            name = script.replace("/", ".")
            spec = importlib.util.spec_from_file_location(name, str(module_path))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore
        finally:
            for p in inserted:
                try:
                    sys.path.remove(p)
                except ValueError:
                    pass
        return module

    def _signal_handler(self, signum, frame) -> None:
        """
        Handle cancellation requests (e.g., Ctrl+C).
        This sets a flag to indicate cancellation and raises a
        GiorgioCancellationError.

        :param signum: The signal number.
        :type signum: int
        :param frame: The current stack frame.
        :type frame: frame
        :returns: None
        :rtype: None
        :raises GiorgioCancellationError: Always raised to indicate
        cancellation.
        """

        self._cancel_requested = True
        raise GiorgioCancellationError("Execution cancelled by user.")

    def run_script(
        self,
        script: str,
        cli_args: Optional[Dict[str, Any]] = None,
        add_params_callback: Optional[Callable[[Dict[str, Dict[str, Any]], Dict[str, str]], Dict[str, Any]]] = None,
    ) -> None:
        """
        Run a user-defined script with the given parameters and environment.

        :param script: The path to the script relative to the scripts directory,
        using forward slashes (e.g., "my_script/script.py").
        :type script: str
        :param cli_args: Optional dictionary of command-line arguments to pass
        to the script. If None, interactive prompts will be used.
        :type cli_args: Optional[Dict[str, Any]]
        :param add_params_callback: Optional callback function to handle
        additional parameters interactively. This should accept a schema
        dictionary and the environment, and return a dictionary of additional
        parameters.
        :type add_params_callback: Optional[Callable[[Dict[str, Dict[str, Any]], Dict[str, str]], Dict[str, Any]]]
        :raises FileNotFoundError: If the script file does not exist.
        :raises RuntimeError: If the script does not define a `run` function
        or if non-interactive mode is used without `cli_args`.
        :raises ValueError: If any parameter validation fails.
        :raises AttributeError: If the script does not define the required
        `run` function.
        :raises GiorgioCancellationError: If the user cancels execution
        (e.g., via Ctrl+C).
        """

        module = self._import_script_module(script)
        schema = getattr(module, "PARAMS", {}) or {}

        # Interactive initial prompts if no cli_args
        if cli_args is None:
            if add_params_callback is None:
                raise RuntimeError("Non-interactive run requires cli_args. Use 'start' for interactive mode.")
            
            initial_params = prompt_for_params(schema, self.env)
            prompt_cb = add_params_callback
        
        else:
            initial_params = {}
            prompt_cb = add_params_callback
            
            for key, meta in schema.items():
                expected = meta.get("type", str)
                required = meta.get("required", False)
                default = meta.get("default", None)
                choices = meta.get("choices")

                if key in cli_args:
                    raw = cli_args[key]

                    if expected is bool:
                        low = str(raw).strip().lower()

                        if low in ("true", "1", "yes", "y"):
                            val = True
                        
                        elif low in ("false", "0", "no", "n"):
                            val = False
                        
                        else:
                            raise ValueError(f"Invalid boolean for '{key}': '{raw}'.")
                    
                    else:
                        try:
                            val = expected(raw)
                    
                        except Exception:
                            raise ValueError(f"Invalid type for parameter '{key}': expected {expected.__name__}.")
                    
                    if choices and val not in choices:
                        raise ValueError(f"Invalid choice '{val}' for parameter '{key}'.")
                    
                    initial_params[key] = val
                
                else:
                    val = default
                    
                    if isinstance(default, str) and default.startswith("${") and default.endswith("}"):
                        env_key = default[2:-1]
                        val = self.env.get(env_key)
                    
                    if val is not None:
                        if expected is bool:
                            low = str(val).strip().lower()

                            if low in ("true", "1", "yes", "y"):
                                converted = True
                            
                            elif low in ("false", "0", "no", "n"):
                                converted = False
                            
                            else:
                                raise ValueError(f"Invalid default boolean for '{key}': '{val}'.")
                        else:
                            try:
                                converted = expected(val)
                            
                            except Exception:
                                raise ValueError(f"Invalid default for '{key}': cannot convert '{val}'.")
                        
                        initial_params[key] = converted
                    
                    elif required:
                        raise RuntimeError(f"Missing required parameter '{key}' in non-interactive mode.")

        context = Context(initial_params, self.env, prompt_cb, self)

        # Use a script-specific child logger so scripts can easily identify
        # their log output. Example logger name: 'giorgio.scripts.my_script'.
        try:
            script_logger_name = f"giorgio.scripts.{script.replace('/', '.')}"
            context.logger = logging.getLogger(script_logger_name)
        except Exception:
            # Fallback to default 'giorgio' logger if anything goes wrong
            context.logger = logging.getLogger("giorgio")

        if not hasattr(module, "run") or not callable(module.run):
            raise AttributeError(f"Script '{script}' must define run(context).")

        prev_handler = None
        if sys.platform != "win32":
            prev_handler = signal.signal(signal.SIGINT, self._signal_handler)
        
        try:
            module.run(context)
        
        except GiorgioCancellationError:
            print("Script execution cancelled.", flush=True)
        
        except KeyboardInterrupt:
            print("Script execution cancelled (KeyboardInterrupt).", flush=True)
        
        finally:
            if prev_handler and sys.platform != "win32":
                signal.signal(signal.SIGINT, prev_handler)
