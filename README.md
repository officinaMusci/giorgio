# Giorgio

Giorgio is a lightweight micro-framework for script automation with a GUI.
It allows you to manage and run your automation scripts via a graphical
interface and a set of CLI commands.

## Features

- Dynamic detection of user and internal scripts.
- Configurable GUI built with Tkinter.
- CLI commands to initialize a new project, generate new scripts,
  start the GUI, and build your project.

## Installation

Install via pip:

```bash
pip install giorgio
```

## CLI Commands

- **init**: Initializes a new Giorgio project in the current directory
  (creates a `scripts` folder, a `config.json` file, and a README.md).
- **new-script \<script_name\>**: Generates a new blank script in the `scripts`
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