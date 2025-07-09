# Changelog

All notable changes to this project will be documented in this file.

## 1.3.0 (2025-07-09)

### Feat

- add version information to upgrade_project function

## [1.2.5] - 2025-07-08

### Added
- UI plugin discovery.
- Path prompt support.
- Usage information for scripts.
- PEP 621 (`pyproject.toml`) packaging.

### Fixed
- UI issues in `giorgio start`.
- Behavior of additional parameters.

### Changed
- Workflow model replaced with trunk-based CI, Commitizen integration, and updated README.
- Removal of hard-coded `__init__.py` version file.
- Code optimizations and readability improvements.

## [1.0.0] - 2025-06-19

### Added
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

### Fixed
- Parameter type conversion and boolean parsing in non-interactive mode.
- Environment variable substitution for default parameter values.
- Preservation of single-responsibility and DRY principles in code modules.