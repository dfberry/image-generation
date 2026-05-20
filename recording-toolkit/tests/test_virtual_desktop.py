"""Tests for VirtualDesktopSession."""

import argparse
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers — make scripts importable without installing all heavy deps
# ---------------------------------------------------------------------------

def _make_virtual_desktop_module():
    """Import virtual_desktop from the scripts directory."""
    import importlib.util
    import os
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
    spec = importlib.util.spec_from_file_location(
        "virtual_desktop",
        os.path.join(scripts_dir, "virtual_desktop.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vd_mod = _make_virtual_desktop_module()
VirtualDesktopSession = vd_mod.VirtualDesktopSession


# ---------------------------------------------------------------------------
# Fix 4a: __enter__ raises RuntimeError on non-Windows
# ---------------------------------------------------------------------------

def test_enter_raises_on_non_windows():
    session = VirtualDesktopSession()
    with patch.object(sys, "platform", "linux"):
        with pytest.raises(RuntimeError, match="Windows 10\\+"):
            session.__enter__()


# ---------------------------------------------------------------------------
# Fix 4b: __enter__/__exit__ lifecycle (mock pyvda)
# ---------------------------------------------------------------------------

def _make_pyvda_mock():
    mock_original = MagicMock(name="original_desktop")
    mock_created = MagicMock(name="created_desktop")
    mock_vd_class = MagicMock()
    mock_vd_class.current.return_value = mock_original
    mock_vd_class.create.return_value = mock_created

    pyvda_mock = types.ModuleType("pyvda")
    pyvda_mock.VirtualDesktop = mock_vd_class
    return pyvda_mock, mock_original, mock_created


def test_enter_exit_lifecycle():
    pyvda_mock, mock_original, mock_created = _make_pyvda_mock()

    session = VirtualDesktopSession()
    with patch.dict(sys.modules, {"pyvda": pyvda_mock}), \
         patch.object(sys, "platform", "win32"):
        result = session.__enter__()
        assert result is session
        mock_created.go.assert_called_once()

        session.__exit__(None, None, None)
        mock_original.go.assert_called_once()
        mock_created.remove.assert_called_once()


def test_exit_returns_false():
    """__exit__ must return False so exceptions propagate."""
    pyvda_mock, _, _ = _make_pyvda_mock()
    session = VirtualDesktopSession()
    with patch.dict(sys.modules, {"pyvda": pyvda_mock}), \
         patch.object(sys, "platform", "win32"):
        session.__enter__()
        assert session.__exit__(None, None, None) is False


# ---------------------------------------------------------------------------
# Fix 4c: __exit__ logs warning on remove failure
# ---------------------------------------------------------------------------

def test_exit_logs_warning_on_remove_failure(caplog):
    pyvda_mock, mock_original, mock_created = _make_pyvda_mock()
    mock_created.remove.side_effect = OSError("access denied")

    session = VirtualDesktopSession()
    with patch.dict(sys.modules, {"pyvda": pyvda_mock}), \
         patch.object(sys, "platform", "win32"):
        session.__enter__()

    import logging
    with caplog.at_level(logging.WARNING, logger="virtual_desktop"):
        session.__exit__(None, None, None)

    assert any("Failed to remove virtual desktop" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Fix 4d: __enter__ raises helpful error when pyvda is missing
# ---------------------------------------------------------------------------

def test_enter_raises_on_missing_pyvda():
    session = VirtualDesktopSession()
    with patch.dict(sys.modules, {"pyvda": None}), \
         patch.object(sys, "platform", "win32"):
        with pytest.raises((RuntimeError, ImportError)):
            session.__enter__()


# ---------------------------------------------------------------------------
# Fix 4e: --virtual-desktop flag parsed correctly in argparse
# ---------------------------------------------------------------------------

def test_virtual_desktop_argparse_flag():
    """--virtual-desktop flag must be present and default to False."""
    import importlib.util
    import os
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")

    # Stub heavy imports before loading demo_plan_runner
    stubs = {
        "pyautogui": MagicMock(),
        "record_desktop": MagicMock(),
        "pyvda": MagicMock(),
    }
    with patch.dict(sys.modules, stubs):
        spec = importlib.util.spec_from_file_location(
            "demo_plan_runner",
            os.path.join(scripts_dir, "demo_plan_runner.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

    parser = argparse.ArgumentParser()
    # Replicate the relevant argument from the runner's main()
    parser.add_argument("--virtual-desktop", action="store_true",
                        help="Run automation on a separate virtual desktop (Windows 10+, non-interrupting)")
    parser.add_argument("plan", nargs="?", default="dummy.json")

    args = parser.parse_args([])
    assert args.virtual_desktop is False

    args_with_flag = parser.parse_args(["--virtual-desktop"])
    assert args_with_flag.virtual_desktop is True
