# Giorgio - Automation Framework

*A lightweight, extensible micro‑framework for fast, friendly automation scripts.*

<p>
    <!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
    <a href="https://pypi.org/project/giorgio">
        <img alt="PyPI Version" src="https://badge.fury.io/py/giorgio.svg"/>
    </a>
    <a href="https://www.python.org/downloads/release/python-380/">
        <img alt="Python Version" src="https://img.shields.io/badge/python-3.10%2B-blue.svg"/>
    </a>
    <a href="https://codecov.io/gh/officinaMusci/giorgio">
        <img alt="Codecov Coverage" src="https://codecov.io/gh/officinaMusci/giorgio/branch/main/graph/badge.svg"/>
    </a>
    <a href="./LICENSE">
        <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-green.svg"/>
    </a>
</p>

Giorgio helps you scaffold, run, and compose automation scripts—from one‑off utilities to ambitious prototypes—without the ceremony. Think of it as a courteous digital butler: it asks the right questions, remembers your preferences, and carries out your instructions with minimal fuss.

---

## Table of contents

- [Giorgio - Automation Framework](#giorgio---automation-framework)
  - [Table of contents](#table-of-contents)
  - [Why Giorgio?](#why-giorgio)
  - [Features](#features)
  - [Installation](#installation)
  - [Quick start](#quick-start)
    - [Initialize a project](#initialize-a-project)
    - [Scaffold a script](#scaffold-a-script)
    - [Generate a script with AI (vibe‑coding)](#generate-a-script-with-ai-vibecoding)
    - [Run interactively or automatically](#run-interactively-or-automatically)
  - [Project layout](#project-layout)
  - [Script anatomy](#script-anatomy)
    - [1. CONFIG](#1-config)
    - [2. PARAMS](#2-params)
    - [3. `run(context)`](#3-runcontext)
    - [The `Context` API](#the-context-api)
  - [Composing automations](#composing-automations)
  - [Configuration \& environment variables](#configuration--environment-variables)
  - [CLI reference](#cli-reference)
  - [Scheduling (Cron / Task Scheduler)](#scheduling-cron--task-scheduler)
  - [Tips \& best practices](#tips--best-practices)
  - [Contributing](#contributing)
  - [License](#license)

---

## Why Giorgio?

Script files are quick to write—until they aren’t. Once you add parameters, validation, prompts, environment variables, and a touch of UX, the "quick script" becomes an accidental framework. Giorgio gives that structure to you from the start: a clean scaffold, a type‑safe parameter system, an interactive runner, and an optional AI‑powered script generator that turns plain‑language ideas into working code.

**Use Giorgio when you want:**

- Rapid local automations with a consistent shape.
- Interactive runs that ask for what’s missing, or non‑interactive runs suitable for Cron.
- A clear migration path from small scripts to reusable building blocks.
- To generate boilerplate (or whole scripts) from a description using any OpenAI‑compatible API.

## Features

- **Instant scaffolding** with a best‑practice directory layout.
- **Script generator** from templates or via *vibe‑coding* using an OpenAI‑compatible API.
- **Interactive CLI** with dynamic prompts and live output, or **fully automated** runs.
- **Type‑safe parameters** with custom types, choices, and validation.
- **Environment variable** placeholders and `.env` loading.
- **Composable automation**: call other scripts from your script.
- **Pluggable UI renderers** for tailored interactive experiences.
- **Minimal setup, maximum extensibility**: configure only what you need.

## Installation

Giorgio supports **Python 3.10+**. Installing with **pipx** keeps your CLI isolated and on your PATH:

```bash
pipx install giorgio
```

Alternatively, use pip in a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install giorgio
```

> **Note**
> For AI‑powered generation you’ll need an OpenAI‑compatible endpoint and API key (see [Generate a script with AI](#generate-a-script-with-ai-vibe-coding)).

## Quick start

### Initialize a project

```bash
giorgio init my_project
cd my_project
```

Creates a clean structure with dedicated folders for **scripts**, shared **modules**, and configuration.

### Scaffold a script

```bash
giorgio new cleanup_logs
```

This creates `scripts/cleanup_logs/script.py` with a ready‑to‑edit skeleton (`CONFIG`, `PARAMS`, and `run(context)`).

> **Note**
> Scripts can also be created in subdirectories, e.g.:
> 
> ```bash
> giorgio new cleansing/cleanup_logs
> ```
> 
> This will create `scripts/cleansing/cleanup_logs/script.py`.

### Generate a script with AI (vibe‑coding)

```bash
giorgio new greet_user --ai-prompt "Create a script that prints a text provided as a parameter"
```

When using `--ai-prompt`, Giorgio may also ask to include project modules or existing scripts as **context** to improve generation. The result follows Giorgio’s conventions and includes inline documentation.

**Environment** (typical):

You can set environment variables directly in your shell, or place them in your project’s `.env` file (recommended for local development):

```bash
export AI_API_KEY=...
export AI_BASE_URL=https://my-endpoint.example/v1
export AI_API_MODEL=my-favorite-model
export AI_TEMPERATURE=0.2         # (optional) Controls randomness, default 0.0
export AI_MAX_TOKENS=2048         # (optional) Max output tokens, default unlimited
```

Or in `.env`:

```
AI_API_KEY=...
AI_BASE_URL=https://my-endpoint.example/v1
AI_API_MODEL=my-favorite-model
AI_TEMPERATURE=0.2
AI_MAX_TOKENS=2048
```

### Run interactively or automatically

**Interactive mode**: Prompts you to select a script, then asks for parameters.

```bash
giorgio start
```

**Automated (non-interactive) mode**: Runs the specified script directly. You must provide all required parameters (or ensure they have defaults).

```bash
giorgio run cleanup_logs --param days=30 --param log_dir=/var/logs
```

Use interactive mode for guided runs and parameter prompts; use non-interactive mode for automation and scripting (e.g., in Cron jobs).

## Project layout

After `giorgio init my_project`:

```
my_project/
├─ .giorgio/config.json
├─ modules/
│  └─ __init__.py
├─ scripts/
└─ .env
```

<!-- BEGIN GIORGIO_SCRIPT_ANATOMY -->
## Script anatomy

Every Giorgio script follows a standard structure: **CONFIG**, **PARAMS**, and a `run(context)` function.

### 1. CONFIG

`CONFIG` is optional metadata shown in interactive mode.

```python
CONFIG = {
    "name": "Cleanup Logs",
    "description": "Remove old log files from a target directory."
}
```

### 2. PARAMS

`PARAMS` declares **all inputs** the script needs. Giorgio validates types, applies defaults, and—if running interactively—prompts for anything missing.

Supported attributes:

- `type` *(required)* — validates and converts the value (e.g. `str`, `int`, `bool`, `Path`, or custom classes).
- `default` *(optional)* — a fallback value; supports `${VAR_NAME}` placeholders for environment variables.
- `description` *(optional)* — a short help text.
- `choices` *(optional)* — restricts input to a predefined list of values.
- `multiple` *(optional)* — allow selection of multiple values (with `choices`).
- `required` *(optional)* — mark the parameter as mandatory.
- `validation` *(optional)* — a function that returns `True` or an error message.

Example:

```python
from pathlib import Path

PARAMS = {
    "confirm": {
        "type": bool,
        "default": False,
        "description": "Whether to confirm the action.",
    },
    "days": {
        "type": int,
        "default": 30,
        "description": "Delete files older than N days.",
        "validation": lambda x: x > 0 or "Days must be a positive integer."
    },
    "log_dir": {
        "type": Path,
        "description": "Directory containing log files.",
        "required": True
    },
    "level": {
        "type": str,
        "choices": ["debug", "info", "warning", "error"],
        "description": "Logging verbosity.",
    },
    "options": {
        "type": str,
        "choices": ["dry_run", "force"],
        "multiple": True,
        "description": "Optional flags."
    },
    "environment_var": {
        "type": str,
        "default": "${MY_ENV_VAR}",
        "description": "Value read from env if set."
    }
}
```

### 3. `run(context)`

`run(context)` is the script’s entry point. It receives a `Context` object providing everything needed at runtime.

```python
from pathlib import Path
from giorgio.execution_engine import Context, GiorgioCancellationError


def run(context: Context):
    try:
        log_dir: Path = context.params["log_dir"]
        days: int = context.params["days"]

        print(f"Cleaning logs older than {days} days in {log_dir}…")

        # Example of dynamic prompting (interactive mode only)
        context.add_params({
            "confirm": {
                "type": bool,
                "description": "Are you sure you want to delete these files?",
                "default": False,
            }
        })

        if context.params["confirm"]:
            # Compose with another Giorgio script
            context.call_script("delete_files", {"target_dir": log_dir})
            print("Cleanup completed.")
        else:
            print("Operation cancelled.")

    except GiorgioCancellationError:
        print("Script execution cancelled by the user.")
```

### The `Context` API

The `Context` object exposes:

* **Validated parameters** — `context.params["key"]`.
* **Environment variables** — `context.env["VAR"]` (loads from `.env` and the system).
* **Dynamic prompting** — `context.add_params({...})` to ask for more inputs at runtime (interactive mode only).
* **Composition** — `context.call_script(name, params)` to run other Giorgio scripts programmatically.
* **Logging** — `context.logger` exposes standard logging methods (debug/info/warning/error); the engine replaces it with a script-specific child logger `giorgio.scripts.<script_path>` when a script runs.
* **Output** — standard `print()` and other output streams are supported; UI renderers may capture and display these outputs in interactive mode.
<!-- END GIORGIO_SCRIPT_ANATOMY -->

## Composing automations

Scripts are building blocks. You can invoke one script from another to create small, readable steps that add up to robust flows.

```python
def run(context):
    # Normalize inputs in one script…
    context.call_script("normalize_dataset", {"src": "./raw.csv"})
    # …then pass results into the next one.
    context.call_script("train_model", {"epochs": 10, "lr": 0.001})
```

Composition keeps each script focused and testable while enabling richer automations.

## Configuration & environment variables

Giorgio reads environment variables from the OS and, if present, from a local `.env` file at project root. Within `PARAMS`, you may reference variables using `${VAR_NAME}` in `default` values; these expand at runtime.

**Supported AI environment variables:**

- `AI_API_KEY` — API key for your OpenAI-compatible endpoint (**required**)
- `AI_BASE_URL` — Base URL for the API (**required**)
- `AI_MODEL` or `AI_API_MODEL` — Model name (**required**)
- `AI_TEMPERATURE` — *(optional)* Controls randomness (float, default: 0.0)
- `AI_MAX_TOKENS` — *(optional)* Maximum output tokens (int, default: unlimited)

Example `.env`:

```
DATA_DIR=./data
MY_ENV_VAR=hello
```

Example `PARAMS` default using an env placeholder:

```python
"data_dir": {
    "type": Path,
    "default": "${DATA_DIR}",
    "description": "Where datasets are stored."
}
```

## CLI reference

```
giorgio init <project_name>
    Create a new Giorgio project (folders for scripts, modules, config).

giorgio new <script_name> [--ai-prompt "…"]
    Scaffold a new script. With --ai-prompt, generate code via an OpenAI‑compatible API.

giorgio start
    Launch interactive mode. Select a script; Giorgio prompts for missing params.

giorgio run <script_name> --param key=value [--param key=value ...]
    Run non‑interactively (suitable for Cron). Provide all required params.

giorgio --help
    Show general help and options.
```

> **Tip**
> Use `--param` repeatedly to pass multiple key/value pairs.

## Scheduling (Cron / Task Scheduler)

**Cron (Linux/macOS):**

```
# Run every night at 02:30
30 2 * * * cd /path/to/my_project && /usr/bin/env giorgio run cleanup_logs \
  --param days=30 --param log_dir=/var/logs >> cron.log 2>&1
```

**Windows Task Scheduler:** create a task that executes:

```
C:\\Path\\To\\Python\\Scripts\\giorgio.exe run cleanup_logs --param days=30 --param log_dir=C:\\Logs
```

## Tips & best practices
- **Keep scripts small and focused.** Compose multiple scripts for larger automation flows to maximize clarity and reusability.
- **Declare all inputs in `PARAMS`.** Avoid using implicit globals; explicit parameters improve validation and documentation.
- **Leverage `choices` and `validation`.** Define allowed values and validation logic to catch errors early and guide users.
- **Encapsulate reusable logic in `modules/`.** Place shared functions and utilities in the `modules/` directory and import them into your scripts.
- **Use `context.add_params()` for dynamic prompting.** Prefer Giorgio’s built-in parameter prompting over other package methods or native Python functions like `input()`. This ensures consistent UX, validation, and compatibility with both interactive and automated runs.
- **Reserve AI generation for boilerplate or drafts.** Use AI-powered script generation to accelerate prototyping, but always review and refine generated code before use.
- **Handle secrets securely.** Store API keys and sensitive data in your `.env` file (excluded from version control) or your OS keychain—never hard-code them.
- **Review AI-generated code before production use.** Always inspect and test code generated by AI before deploying in critical environments.
- **Avoid logging secrets.** Redact or exclude sensitive information from logs to prevent accidental exposure.

## Contributing

Community contributions are welcome and encouraged. To maintain a smooth and manageable workflow, please adhere to the following guidelines.

Development follows a trunk-based workflow using short-lived branches created from `main`. When your changes are complete and stable, open a pull request (PR) targeting `main`. This approach ensures the codebase remains up-to-date and avoids long-lived branches.

Please write commit messages according to the [Conventional Commits](https://www.conventionalcommits.org/) specification. To make this easier, use the [commitizen](https://commitizen-tools.github.io/commitizen/) tool, which helps you generate properly formatted commit messages. You can run `cz commit` instead of `git commit` to be guided through the process.

All pull requests against `main` trigger the [CI workflow](./.github/workflows/ci.yml), which runs linting, tests across Python 3.10–3.12 on Linux, macOS, and Windows, and enforces the coverage threshold. After a push to the `main` branch, the [version bump workflow](./.github/workflows/bump.yml) runs to bump the version with Commitizen and update `CHANGELOG.md`, pushing the new `v*` tag. Pushing that tag then triggers the [publish workflow](./.github/workflows/publish.yml) to run final tests & coverage upload, build the distribution, and publish the package to PyPI.

**Please ensure that every contribution includes appropriate tests.** Adding or updating tests helps maintain code quality and reliability for all users.

Thank you for contributing to Giorgio!

## License

This project is licensed under the terms of the [MIT License](./LICENSE). Refer to the `LICENSE` file for full license text.

---

*Happy automating with Giorgio!*