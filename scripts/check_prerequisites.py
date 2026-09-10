#!/usr/bin/env python3
"""Phase 0: verify local prerequisites before starting Phase 1."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIN_PYTHON = (3, 11)


def _ok(msg: str) -> None:
    print(f"  [OK]  {msg}")


def _warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def check_python() -> bool:
    version = sys.version_info[:2]
    if version >= MIN_PYTHON:
        _ok(f"Python {sys.version.split()[0]} (>= {MIN_PYTHON[0]}.{MIN_PYTHON[1]})")
        return True
    _fail(
        f"Python {sys.version.split()[0]} found; "
        f"need {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ (see README)"
    )
    return False


def check_venv() -> bool:
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if in_venv:
        _ok(f"Virtual environment active ({sys.prefix})")
        return True
    _warn("No virtual environment detected — create with: python3.11 -m venv .venv")
    return True  # soft warning; do not block


def check_gitignore() -> bool:
    path = PROJECT_ROOT / ".gitignore"
    if not path.exists():
        _fail(".gitignore missing")
        return False
    text = path.read_text(encoding="utf-8")
    required = [".env", "venv/", "data/"]
    missing = [item for item in required if item not in text]
    if missing:
        _fail(f".gitignore missing patterns: {missing}")
        return False
    _ok(".gitignore present (excludes .env, venv, data)")
    return True


def check_env_example() -> bool:
    path = PROJECT_ROOT / ".env.example"
    if not path.exists():
        _fail(".env.example missing")
        return False
    _ok(".env.example present")
    return True


def check_env_file() -> bool:
    path = PROJECT_ROOT / ".env"
    if not path.exists():
        _warn(".env not found — copy .env.example to .env and add your API key")
        return True  # Phase 0 allows missing key until LLM phase
    _ok(".env file present")
    return True


def check_settings_load() -> bool:
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from src.config.settings import get_settings

        settings = get_settings()
        _ok(
            f"Settings load OK (provider={settings.llm_provider}, "
            f"model={settings.llm_model})"
        )
        key = settings.api_key_for_provider()
        if settings.llm_provider == "ollama":
            _ok("LLM provider is ollama (no cloud API key required)")
        elif key:
            _ok(f"API key configured for provider '{settings.llm_provider}'")
        elif settings.llm_provider == "groq":
            _warn(
                "GROQ_API_KEY is not set in .env "
                "(required for Phase 3 — get one at https://console.groq.com/)"
            )
        else:
            _warn(
                f"No API key set for provider '{settings.llm_provider}' "
                "(required from Phase 3 onward)"
            )
        return True
    except Exception as exc:  # noqa: BLE001 — report any bootstrap failure
        _fail(f"Could not load settings: {exc}")
        return False


def check_network_tools() -> bool:
    if shutil.which("git") is None:
        _warn("git not found on PATH")
    else:
        _ok("git available")
    return True


def check_scaffold() -> bool:
    required_dirs = [
        "src/config",
        "src/data",
        "src/models",
        "src/filters",
        "src/llm/providers",
        "src/services",
        "src/api",
        "app/components",
        "tests",
        "scripts",
        "data/processed",
        "Docs",
    ]
    missing = [d for d in required_dirs if not (PROJECT_ROOT / d).exists()]
    if missing:
        _fail(f"Missing directories: {missing}")
        return False
    _ok("Project scaffold directories present")
    return True


def main() -> int:
    print("Phase 0 — prerequisite check\n")
    checks = [
        check_python(),
        check_venv(),
        check_gitignore(),
        check_env_example(),
        check_env_file(),
        check_scaffold(),
        check_network_tools(),
        check_settings_load(),
    ]
    print()
    if all(checks):
        print("Result: READY for Phase 1 (fix any WARN items before Phase 3).")
        return 0
    print("Result: NOT READY — fix FAIL items above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
