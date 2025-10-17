# Giorgio AI Briefing
## Core Flow
- `giorgio/cli.py` is the Typer CLI entry; `pyproject.toml` maps the `giorgio` console script here. `configure_logging` runs on import to honor `.giorgio/config.json` logging levels and uses Rich for output.
- `service` commands: `init` scaffolds project structure, `new` delegates to `project_manager.create_script`, `run` executes scripts non-interactively, `start` wires interactive UI renderers, `validate` runs static checks, `upgrade` reconciles configured vs installed versions.

## Execution Model
- `giorgio/execution_engine.py` loads `.env` via python-dotenv if available; if `.env` exists without the library installed, it raises a `RuntimeError` (tests enforce this).
- `ExecutionEngine.run_script(script, cli_args, add_params_callback)` imports `scripts/<name>/script.py`, prepends configured `module_paths` (from `.giorgio/config.json`) to `sys.path`, and ensures each path is a package by touching `__init__.py`.
- Scripts must define literal `CONFIG`, `PARAMS`, and a `run(context)` callable; `Context` exposes read-only params, the merged env, a script-specific logger (`giorgio.scripts.<path>`), `.add_params()` (interactive only), and `.call_script()` for composition.
- Non-interactive runs require every required parameter; bool parameters coerce strings like `true/false/1/0/yes/no`, and defaults can reference environment placeholders (`${VAR}`) that resolve through `self.env`.

## Interactive UX
- `giorgio/prompt.py` centralizes questionary prompts. `ScriptFinder` walks `scripts/` and parses `CONFIG["name"]` via AST so menu labels stay in sync with script metadata.
- UI plugins implement `giorgio/ui_renderer.py::UIRenderer`; the built-in `CLIUIRenderer` links script selection and parameter prompting. Additional renderers register under the `giorgio.ui_renderers` entry point in `pyproject.toml`.

## Project Management
- `project_manager.py` owns project scaffolding, script creation, upgrades, and config IO. `module_paths` let projects expose shared packages; `create_script` ensures intermediate packages include `__init__.py` and hydrates `templates/script_template.py` (replacing `__SCRIPT_PATH__`).
- `validation.py` performs AST-only enforcement of CONFIG/PARAMS/run; CLI `validate` and `upgrade` rely on its summaries, so keep new script metadata literal-friendly.

## AI Generation
- `ai_client.py` wraps Instructor + OpenAI SDK. It expects `AI_API_KEY`, `AI_BASE_URL`, and `AI_MODEL` (optional `AI_TEMPERATURE`, `AI_MAX_TOKENS`) and will re-load `.env` when instantiating `AIScriptingClient`.
- `AIScriptingClient.generate_script()` seeds prompts with `templates/script_template.py` and the README block between `<!-- BEGIN/END GIORGIO_SCRIPT_ANATOMY -->`; if those markers move, tests in `tests/test_ai_client.py` will fail.

## Developer Workflow
- Install locally with `pip install -e .` (project deps: Typer, Questionary, python-dotenv, instructor, openai, rich), and add `pytest` for the test suite.
- Run tests with `pytest`; suites cover CLI flows (`tests/test_cli.py`), execution engine edge cases (`tests/test_execution_engine.py`), prompt helpers, AI client behaviour, and validation rules.
- CLI tests lean on `typer.testing.CliRunner` and heavy monkeypatching of `questionary`; prefer injecting collaborators inside functions to keep tests patchable.

## Gotchas
- `Context.add_params` raises unless an interactive callback exists; preserve this guard when extending interactive flows.
- `ExecutionEngine` temporarily mutates `sys.path`; always restore new insertions in `finally` blocks to keep re-entrant calls safe.
- Keep README markers and template paths accurate; AI generation and related tests assume their current locations and names.
