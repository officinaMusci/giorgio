# Giorgio - Automation Framework

<p>
    <!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
    <a href="https://github.com/officinaMusci/giorgio/actions/workflows/main-deploy.yml">
        <img alt="Build Status" src="https://github.com/officinaMusci/giorgio/actions/workflows/main-deploy.yml/badge.svg"/>
    </a>
    <a href="https://pypi.org/project/giorgio">
        <img alt="PyPI Version" src="https://badge.fury.io/py/giorgio.svg"/>
    </a>
    <a href="https://codecov.io/gh/officinaMusci/giorgio">
        <img alt="Codecov Coverage" src="https://codecov.io/gh/officinaMusci/giorgio/branch/main/graph/badge.svg"/>
    </a>
    <a href="./LICENSE">
        <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-green.svg"/>
    </a>
    <a href="https://officina.musci.ch/giorgio">
        <img alt="Docs" src="https://img.shields.io/badge/docs-latest-blue.svg"/>
    </a>
    <br>
    <a href="https://github.com/officinaMusci/giorgio/commits/main">
        <img alt="GitHub commit activity" src="https://img.shields.io/github/commit-activity/m/officinaMusci/giorgio"/>
    </a>
    <a href="https://github.com/officinaMusci/giorgio/commits/main">
        <img alt="Github Last Commit" src="https://img.shields.io/github/last-commit/officinaMusci/giorgio"/>
    </a>
    <a href="https://github.com/officinaMusci/giorgio/graphs/contributors">
        <img alt="Github Contributors" src="https://img.shields.io/github/contributors/officinaMusci/giorgio"/>
    </a>
    <a href="https://github.com/officinaMusci/giorgio/issues">
        <img alt="GitHub open issues" src="https://img.shields.io/github/issues/officinaMusci/giorgio"/>
    </a>
    <a href="https://github.com/officinaMusci/giorgio/issues?q=is%3Aissue+is%3Aclosed">
        <img alt="GitHub closed issues" src="https://img.shields.io/github/issues-closed/officinaMusci/giorgio"/>
    </a>
</p>

Giorgio is a lightweight, extensible Python micro-framework designed to scaffold, execute, and manage automation scripts. Whether you prefer interactive CLI prompts or fully non-interactive execution for CI/CD pipelines, Giorgio provides a consistent developer experience with minimal boilerplate.

## 🚀 Installation

Install the latest release from PyPI:

```bash
pip install giorgio
```

For development or to contribute:

```bash
pip install --index-url https://test.pypi.org/simple/ giorgio
```

> ⚠️ Ensure your environment meets **Python ≥ 3.7**.

## 📂 Project Layout

```text
.
├── .env                   # Optional environment variables (loaded on run/start)
├── scripts/               # Your automation scripts
│   └── my_script/         # Each script has its own folder
│       ├── script.py      # CORE: CONFIG, PARAMS, run(context)
│       └── templates/      # (Optional) helper files for the script
├── modules/               # Shared Python modules for cross-script reuse
└── .giorgio/              # Giorgio metadata (config.json)
    └── config.json        # Tracks project version, module paths, etc.
```

## ⚡ Quick Start

### 1. Initialize a Project

```bash
giorgio init [--name PATH]
```

- Creates the recommended directories and files.
- Generates `.env` (empty) and `.giorgio/config.json` with default settings.

### 2. Scaffold a New Script

```bash
giorgio new my_script
```

- Creates `scripts/my_script/` with a starter `script.py`.
- Includes boilerplate for **CONFIG**, **PARAMS**, and a stubbed `run()`.

### 3. Run Scripts

#### Non-interactive (for automation):

```bash
giorgio run my_script \
  --param input_file=./data.txt \
  --param count=5
```

- All required parameters must be provided.
- Supports boolean flags, lists, and environment placeholder defaults (`${VAR}`).

#### Interactive (exploratory):

```bash
giorgio start
```

- Presents a menu of available scripts.
- Prompts you for each parameter with validation, defaults, and help texts.
- Streams `print()` output live to your terminal.
- Press Ctrl+C to abort safely.

## 🛠 Script Development Guide

Inside your `script.py`, define:

```python
from giorgio.execution_engine import GiorgioCancellationError

# 1. CONFIG (optional)
CONFIG = {
    "name": "My Script",
    "description": "A brief summary of what this script does."
}

# 2. PARAMS (required)
PARAMS = {
    "input_path": {
        "type": str,
        "description": "Path to the input file.",
        "required": True
    },
    "dry_run": {
        "type": bool,
        "default": False,
        "description": "If true, do not write any changes."
    },
    "choices": {
        "type": str,
        "choices": ["optA", "optB"],
        "description": "Select one of the options."
    }
}

# 3. run() entrypoint
def run(context):
    try:
        # Access your values
        path = context.params["input_path"]
        
        if params["dry_run"]:
            print("Running in dry-run mode...")
        
        # Example of nested call
        # context.call_script("other_script", {"foo": "bar"})
    
    except GiorgioCancellationError:
        print("Execution was cancelled by the user.")
```

- **CONFIG**: Used for auto-generated documentation or UIs.
- **PARAMS**: Defines types, defaults, choices, and custom validators.
- **run(context)**: Receives a `Context` object with:

  - `context.params` (read-only mapping of provided and default values)
  - `context.env` (loaded `.env` and system vars)
  - `context.add_params(schema)` to request more inputs
  - `context.call_script(name, args)` for chained workflows

## 🤝 Contributing

Contributions are welcome at any level!

### 1. Fork & Branch

```bash
git clone https://github.com/officinaMusci/giorgio.git
cd giorgio
git checkout -b feat/awesome-feature
```

### 2. Develop & Document

- Follow PEP 8, DRY, ETC, and SRP principles.
- Follow the Sphinx/reStructuredText (reST) standard for formatting docstrings.

### 3. Test

- Add new tests under `tests/`.
- Aim for high coverage and cover edge cases.
- Run:

```bash
pytest && coverage run -m pytest && coverage report --show-missing
```

### 4. Commit & Push

```bash
git add .
git commit -m "feat: add awesome feature"
git push origin feat/awesome-feature
```

### 5. Pull Request

- Open a PR against `dev`.
- Describe your changes and link any relevant issues.

Project maintainers will review your PR and merge once it meets quality standards.

## 📝 License

This project is licensed under the terms of the [MIT License](./LICENSE). Refer to the `LICENSE` file for full license text.

---

*Happy automating with Giorgio!*
