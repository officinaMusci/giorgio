# Giorgio - Automation Framework

<p>
    <!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
    <a href="https://pypi.org/project/giorgio">
        <img alt="PyPI Version" src="https://badge.fury.io/py/giorgio.svg"/>
    </a>
    <a href="https://www.python.org/downloads/release/python-380/">
        <img alt="Python Version" src="https://img.shields.io/badge/python-3.8%2B-blue.svg"/>
    </a>
    <br>
    <a href="https://github.com/officinaMusci/giorgio/actions/workflows/main-deploy.yml">
        <img alt="Build Status" src="https://github.com/officinaMusci/giorgio/actions/workflows/main-deploy.yml/badge.svg"/>
    </a>
    <a href="https://codecov.io/gh/officinaMusci/giorgio">
        <img alt="Codecov Coverage" src="https://codecov.io/gh/officinaMusci/giorgio/branch/main/graph/badge.svg"/>
    </a>
    <a href="./LICENSE">
        <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-green.svg"/>
    </a>
</p>

Giorgio is a lightweight, extensible Python micro-framework designed to scaffold, execute, and manage automation scripts. Whether you prefer interactive CLI prompts or fully non-interactive execution, Giorgio provides a consistent developer experience with minimal boilerplate.

## Features

- **Instant project scaffolding** with a best-practice directory layout.
- **Script generator** for rapid creation of parameterized automation scripts.
- **Flexible execution modes**: interactive CLI prompts or fully automated runs.
- **Type-safe parameter system** supporting custom types and validation.
- **Seamless environment variable support** for dynamic configuration.
- **Composable automation**: easily invoke scripts from within other scripts.
- **Minimal setup, maximum extensibility**—configure only what you need.

## Installation

Install Giorgio from PyPI:

```bash
pip install giorgio
```

If you want to install the latest development version or contribute:

```bash
pip install --index-url https://test.pypi.org/simple/ giorgio
```

For local development, consider cloning the repository and installing in editable mode:

```bash
git clone https://github.com/officinaMusci/giorgio.git
cd giorgio
pip install -e .
```

> ⚠️ Ensure your environment meets **Python ≥ 3.8**.

## Quick Start

### 1. Initialize a Project

To kickstart your Giorgio project, run the following command in your terminal:

```bash
giorgio init [--name PATH] # Defaults to current directory
```

When you initialize a project, Giorgio sets up the recommended directory structure and essential files for you. It automatically generates an empty `.env` file for environment variables, along with a `.giorgio/config.json` file pre-populated with default settings, ensuring your project is ready for immediate development.

This command creates the following structure:

```text
.
├── .env               # Optional environment variables (loaded on run/start)
├── scripts/           # Your automation scripts
├── modules/           # Shared Python modules for cross-script reuse
└── .giorgio/          # Giorgio metadata (config.json)
    └── config.json    # Tracks project version, module paths, etc.
```

### 2. Scaffold a New Script

To create a new automation script, use the `new` command followed by your desired script name:

```bash
giorgio new my_script
```

When you scaffold a new script, Giorgio automatically creates a `scripts/my_script/` directory containing a starter `script.py` file. This file comes pre-populated with boilerplate sections for **CONFIG** and **PARAMS**, as well as a stubbed `run()` function, giving you a ready-to-edit foundation for your automation logic.

#### Script Development Guide

Your script should follow a specific structure to ensure compatibility with Giorgio's execution model. Here's a breakdown of the required components:

```python
from giorgio.execution_engine import Context, GiorgioCancellationError

CONFIG = {
    "name": "My Script",
    "description": ""
}

PARAMS = { }


def run(context: Context):
    try:
        # Your script logic goes here
        print("Running the script...")
    
    except GiorgioCancellationError:
        print("Execution was cancelled by the user.")
```

##### `CONFIG` (optional)

The `CONFIG` section allows you to define metadata for your script, such as its name and description. This information is used in the interactive UI to help users understand what the script does.

##### `PARAMS` (required)

The `PARAMS` section defines all the parameters your script requires. Each parameter can specify its `type`, `default` value, `description`, and optional `validation` logic. Giorgio supports standard Python types (`str`, `int`, `float`, `bool`, `Path`) as well as custom classes—if you provide a custom type, Giorgio will instantiate it using the supplied value.

You can enhance parameters with:

- **default**: Sets a fallback value if none is provided. Supports static values or environment variable placeholders using `${VAR_NAME}` syntax, which are resolved from your `.env` file at runtime.
- **choices**: Restricts input to a predefined list of valid options.
- **multiple**: (used with `choices`) Allows users to select more than one option.

Custom validation is supported via a `validation` function that returns `True` or an error message.

This flexible system ensures your scripts are type-safe, user-friendly, and easily configurable for both interactive and automated workflows.

```python
PARAMS = {
    "confirm": {
        "type": bool,
        "default": False,
        "description": "Whether to confirm the action.",
    },
    "count": {
        "type": int,
        "default": 1,
        "description": "Number of times to repeat the action.",
        "validation": lambda x: x > 0 or "Count must be a positive integer."
    },
    "path": {
        "type": Path,
        "description": "Path to your file.",
        "required": True
    },
    "options": {
        "type": str,
        "choices": ["optA", "optB", "optC", "optD"],
        "description": "Select one or more options.",
        "multiple": True
    },
    "custom": {
        "type": MyCustomClass,
        "description": "An instance of MyCustomClass.",
    },
    "environment_var": {
        "type": str,
        "default": "${MY_ENV_VAR}",
        "description": "An environment variable value.",
    }
}
```

##### `run(context)`

The `run(context)` function serves as the main entry point for your script. It receives a `Context` object, which provides convenient access to everything your script needs:

- **Parameter values:** Retrieve user-supplied or defaulted parameters via `context.params`.
- **Environment variables:** Access environment variables loaded from `.env` or the system using `context.env`.
- **Dynamic parameter prompting:** Use `context.add_params()` to request additional input from the user at runtime (available only in interactive mode).
- **Script composition:** Invoke other Giorgio scripts programmatically with `context.call_script()`.

This design enables your scripts to be both flexible and composable, supporting interactive workflows and automation scenarios with minimal boilerplate.

```python
def run(context):
    try:
        # Get the path parameter
        path: Path = context.params["path"]

        # Grab an environment variable (or fall back to a default)
        username = context.env.get("USER", "mysterious_automator")
        print(f"👋 Hello, {username}! Let's see what's in {path}...")

        # Find all .txt files and prompt the user to pick their favorite
        context.add_params({
            "favorite_file": {
                "type": Path,
                "description": "Which text file deserves your attention today?",
                "choices": txt_files,
                "required": True
            }
        })
        favorite = context.params["favorite_file"]
        print(f"🎉 You picked: {favorite.name}")

        # Call another script to celebrate
        context.call_script("celebrate_file", {"file": favorite})

    except GiorgioCancellationError:
        print("🚨 Script execution cancelled! Maybe next time...")
```

### 3. Run Scripts

#### Non-interactive (for automation):

To execute your script non-interactively, you can use the `run` command followed by the script name and any required parameters:

```bash
giorgio run my_script \
  --param input_file=./data.txt \
  --param count=5
```

All required parameters must be provided when running scripts non-interactively. The command supports boolean flags, lists, and allows you to use environment variable placeholders (such as `${VAR}`) as default values for parameters.

#### Interactive (exploratory):

For an interactive experience, simply start Giorgio in interactive mode:

```bash
giorgio start
```

When running in interactive mode, Giorgio presents a menu of available scripts and guides you through each required parameter, providing validation, default values, and helpful descriptions along the way. Output from your script is streamed live to your terminal, allowing you to monitor progress in real time. If you need to stop execution, simply press Ctrl+C to safely abort the process.

## Contributing

Contributions of all kinds—features, bug fixes, documentation, and tests—are welcome. To contribute:

1. **Fork the repository** and create a feature branch from `dev`.
2. **Ensure clarity and maintainability** by following PEP 8 and using Sphinx-style docstrings.
3. **Update or add tests** in the `tests/` directory to cover any changes.
4. **Run tests and check coverage** locally using `pytest` and `coverage`.
5. **Open a pull request** targeting the `dev` branch, summarizing the changes and referencing relevant issues.

All pull requests are reviewed and feedback is provided promptly. When your changes are approved, they will be merged into the `dev` branch. Once a set of features is stable, it will be released to `main`.

Thank you for helping improve Giorgio!

## License

This project is licensed under the terms of the [MIT License](./LICENSE). Refer to the `LICENSE` file for full license text.

---

*Happy automating with Giorgio!*
