# Giorgio

Giorgio is a lightweight micro-framework for automating scripts with a GUI.
It enables you to manage and run your automation scripts through both a graphical interface and a set of CLI commands.

## Features

- Dynamic detection of user and internal scripts.
- Customizable GUI built with Tkinter.
- CLI commands to initialize a new project, create new scripts, launch the GUI, and build your project.

## Installation

Install via pip:

```bash
pip install giorgio
```

## CLI Commands

- **init**: Initializes a new Giorgio project in the current directory
  (creates a `scripts` folder, a `config.json` file, and a README.md).
- **new-script <script_name>**: Generates a new blank script in the `scripts`
  folder using the provided template.
- **start**: Launches the Giorgio GUI.
- **build**: Builds an installable package of your project (not fully implemented).

## Usage

After installing Giorgio, simply run the CLI command:

```bash
giorgio <command> [options]
```

For example, to initialize a new project:

```bash
giorgio init
```

## Contribution Guidelines

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a feature branch (e.g., `feature/my-new-feature`).
3. Commit your changes with clear, descriptive commit messages.
4. Include tests for your changes.
5. Submit a pull request with a detailed description of your modifications.