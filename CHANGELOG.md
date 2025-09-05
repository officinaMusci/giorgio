# Changelog

All notable changes to this project will be documented in this file.

## 1.5.2 (2025-09-05)

### Fix

- update MANIFEST.in and pyproject.toml to include LICENSE and enable package data inclusion

## 1.5.1 (2025-09-05)

### Fix

- add support for loading environment variables from a .env file

## 1.5.0 (2025-09-05)

### Feat

- add module and script selection prompts using questionary
- implement module path loading in ExecutionEngine for dynamic imports
- refactor AIScriptingClient initialization to use project root directly
- enhance AIClient to log assistant messages for improved context tracking
- add fallback schema and remove test for schema validation
- add messages property to AIClient for consolidated message handling
- enhance message handling in AIClient to improve user-assistant interactions and clarify output constraints
- enhance with_doc method to append user-assistant message pairs for context documents
- enhance message handling in AIClient to consolidate system messages
- add script unwrapping functionality to extract Python code from responses
- implement AI script generation in CLI and enhance project management functions

### Fix

- update Python version support to 3.10+ in CI configuration and documentation
- update README.md for clarity and structure, enhancing sections on features, installation, and usage
- rename method to get_script_anatomy_content and extract relevant section from README.md
- update ClientConfig to read temperature and max_output_tokens from environment variables
- update environment variable names for AI configuration in tests
- update AI configuration to use environment variables with AI prefix
- change init command option from --name to positional argument
- update AIScriptingClient to read AI config from environment variables instead of project config
- update with_example method to accept a single example and adjust related prompts
- remove unused strategy parameter from with_doc method
- skip empty __init__.py files and adjust module path resolution
- improve checked logic in _prompt_choices for multiple selections
- remove duplicate code in get_project_config function

### Refactor

- remove unused variables and imports
- update with_examples method to accept a list of examples and improve reset method documentation

## 1.4.0 (2025-07-11)

### Feat

- enhance ScriptFinder to retrieve script names from configuration and improve choice building
- implement ScriptFinder for interactive script selection and navigation

### Fix

- simplify prompt message formatting in ScriptFinder

## 1.3.1 (2025-07-10)

### Fix

- Fix pyproject.toml to include the giorgio package in built distributions

## 1.3.0 (2025-07-09)

### Feat

- add version information to upgrade_project function

## 1.2.5 (2025-07-08)

### Add

- UI plugin discovery.
- Path prompt support.
- Usage information for scripts.
- PEP 621 (`pyproject.toml`) packaging.

### Fix

- UI issues in `giorgio start`.
- Behavior of additional parameters.

### Change

- Workflow model replaced with trunk-based CI, Commitizen integration, and updated README.
- Removal of hard-coded `__init__.py` version file.
- Code optimizations and readability improvements.

## 1.0.0 (2025-06-19)

### Add

- Initial stable release of the Giorgio automation framework.
- `giorgio init`: Initialize a new project layout with `scripts/`, `modules/`, and `.giorgio/config.json`.
- `giorgio new <script>`: Scaffold a new script, including `script.py` template and folder structure.
- `giorgio run <script> --param key=value`: Non-interactive execution with parameter type conversion, defaults, environment variable support, and dynamic call of other scripts.
- `giorgio start`: Interactive mode to select scripts, prompt for parameters via prompts, and handle dynamic additional parameters.
- `UIRenderer` abstract interface for building custom UIs.
- `CLIUIRenderer` implementation using Questionary and stdout.
- Comprehensive pytest test suite covering the execution engine, CLI commands, and project manager.
- GitHub Actions workflows for CI: test matrix, caching, build, and publish to TestPyPI/PyPI using Trusted Publisher.
- Coverage configuration via `.coveragerc`.
- Packaging with setuptools and Typer CLI integration.

### Fix

- Parameter type conversion and boolean parsing in non-interactive mode.
- Environment variable substitution for default parameter values.
- Preservation of single-responsibility and DRY principles in code modules.
