import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from giorgio import logconfig

def _backup_root_logger():
    root = logging.getLogger()
    return root.level, list(root.handlers)


def _restore_root_logger(backup):
    root = logging.getLogger()
    # remove all current handlers
    for h in list(root.handlers):
        root.removeHandler(h)
    # restore handlers
    for h in backup[1]:
        root.addHandler(h)
    root.setLevel(backup[0])


def _clear_root_handlers():
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)


def _get_levels():
    root = logging.getLogger()
    return {
        "root": root.level,
        "giorgio": logging.getLogger("giorgio").level,
        "typer": logging.getLogger("typer").level,
        "click": logging.getLogger("click").level,
    }


def test_level_override_str_and_int_idempotent(tmp_path):
    backup = _backup_root_logger()
    try:
        # ensure no handlers so configure_logging will add one
        _clear_root_handlers()

        # string override
        logconfig.configure_logging(level_override="debug")
        levels = _get_levels()
        assert levels["root"] == logging.DEBUG
        assert levels["giorgio"] == logging.DEBUG
        assert levels["typer"] == logging.DEBUG
        assert levels["click"] == logging.DEBUG

        # idempotent: calling again shouldn't add another handler
        before = len(logging.getLogger().handlers)
        logconfig.configure_logging(level_override="debug")
        after = len(logging.getLogger().handlers)
        assert after == before

        # integer override
        logconfig.configure_logging(level_override=logging.ERROR)
        levels = _get_levels()
        assert levels["root"] == logging.ERROR
        assert levels["giorgio"] == logging.ERROR
        assert levels["typer"] == logging.ERROR
        assert levels["click"] == logging.ERROR
    finally:
        _restore_root_logger(backup)


def test_project_config_nested_and_top_level(tmp_path):
    backup = _backup_root_logger()
    try:
        _clear_root_handlers()

        proj = tmp_path / "proj"
        cfg_dir = proj / ".giorgio"
        cfg_dir.mkdir(parents=True)
        cfg_path = cfg_dir / "config.json"

        # nested form
        cfg_path.write_text(json.dumps({"logging": {"level": "info"}}), encoding="utf-8")
        logconfig.configure_logging(project_root=proj)
        levels = _get_levels()
        assert levels["root"] == logging.INFO
        assert levels["giorgio"] == logging.INFO

        # top-level logging value
        cfg_path.write_text(json.dumps({"logging": "error"}), encoding="utf-8")
        logconfig.configure_logging(project_root=proj)
        levels = _get_levels()
        assert levels["root"] == logging.ERROR
        assert levels["giorgio"] == logging.ERROR
    finally:
        _restore_root_logger(backup)


def test_invalid_config_falls_back_to_warning(tmp_path):
    backup = _backup_root_logger()
    try:
        _clear_root_handlers()

        proj = tmp_path / "proj2"
        cfg_dir = proj / ".giorgio"
        cfg_dir.mkdir(parents=True)
        cfg_path = cfg_dir / "config.json"

        # invalid JSON -> should fall back to WARNING
        cfg_path.write_text("not a json", encoding="utf-8")
        logconfig.configure_logging(project_root=proj)
        levels = _get_levels()
        assert levels["root"] == logging.WARNING
        assert levels["giorgio"] == logging.WARNING
    finally:
        _restore_root_logger(backup)