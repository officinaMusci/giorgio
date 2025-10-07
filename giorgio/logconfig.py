from __future__ import annotations

import json
import logging
from pathlib import Path

from typing import Optional, Union
from rich.logging import RichHandler  # type: ignore


_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "warn": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def _parse_level(value: Optional[Union[str, int]]) -> int:
    """
    Parse a logging level from string or int to int.

    :param value: Logging level as string (e.g. 'info') or int (e.g. logging.INFO).
    :type value: Optional[Union[str, int]]
    :returns: Corresponding logging level as int, or logging.WARNING if parsing fails.
    :rtype: int
    """
    if value is None:
        return logging.WARNING

    if isinstance(value, int):
        return value

    try:
        return _LEVELS.get(str(value).lower(), logging.WARNING)
    except Exception:
        return logging.WARNING


def configure_logging(
    project_root: Optional[Path] = None,
    level_override: Optional[Union[str, int]] = None
) -> None:
    """Configure application-wide logging for Giorgio.

    Priority (highest -> lowest):
      1. level_override if provided
      2. value in project_root/.giorgio/config.json under `logging.level`
      3. WARNING

    The function sets the root logger level (and adds a simple StreamHandler
    if none is present), and also sets the "giorgio", "typer" and "click"
    loggers to the same level so Typer/Click behaviour follows the project's
    setting.

    This function is idempotent: calling it multiple times won't add duplicate
    handlers to the root logger.

    :param project_root: Path to the Giorgio project root directory. If None,
    skips project config lookup.
    :type project_root: Optional[Path]
    :param level_override: Optional logging level to override all other
    settings. Can be string or int.
    :type level_override: Optional[Union[str, int]]
    :returns: None
    :rtype: None
    """
    # Determine level
    level = None
    if level_override is not None:
        level = _parse_level(level_override)

    if level is None and project_root is not None:
        cfg_path = (project_root / ".giorgio" / "config.json").resolve()
        try:
            if cfg_path.exists():
                with cfg_path.open("r", encoding="utf-8") as f:
                    cfg = json.load(f)
                # Nested dict may have 'logging': {'level': 'info'}
                logging_cfg = cfg.get("logging") if isinstance(cfg, dict) else None
                if isinstance(logging_cfg, dict):
                    level = _parse_level(logging_cfg.get("level"))
                else:
                    level = _parse_level(cfg.get("logging"))
        except Exception:
            # If anything goes wrong reading/parsing, fall back to default
            level = None

    if level is None:
        level = logging.WARNING

    # Configure root logger
    root = logging.getLogger()
    root.setLevel(level)

    # Add a Rich handler if none present to ensure CLI output appears.
    # Rich is a declared dependency so import is unconditional.
    if not root.handlers:
        handler = RichHandler(rich_tracebacks=True)
        root.addHandler(handler)

    # Configure package logger and relevant third-party loggers to mirror level
    logging.getLogger("giorgio").setLevel(level)
    # Typer/Click loggers
    logging.getLogger("typer").setLevel(level)
    logging.getLogger("click").setLevel(level)

    # Also mirror warnings to logging
    logging.captureWarnings(True)
