"""Config file loading, in a module that imports NOTHING from `app`.

WHY THIS MODULE EXISTS (#165 lever D). `load_config` used to live in
`app/common/utils.py`, which imports `aiogram` at module level. That made the
function's real cost 8.41-11.06s to import against 0.10-0.14s for the `yaml`
read it actually performs -- measured on this box 2026-11-27 with
`-X importtime`, where `aiogram.types` alone was 4.40s of the chain.

The cost was not academic. `tests/conftest.py` carries an autouse session
fixture, `_validate_llm_config_for_test_session`, which calls
`validate_llm_config` -> `app.common.llm_budget` -> `app.common.utils` ->
`aiogram`. Being autouse, it runs in EVERY pytest session, so each of the 20
pytest-form audit gates paid ~8.7s to import a Telegram client in order to
read a YAML file. Measured: a one-line test file inside `tests/` costs
9.70-11.03s wall, but `--co` (which skips fixtures) costs 0.92-1.19s.

Keeping `load_config` here means the config path is importable without the
bot stack. `app/common/utils.py` re-exports it, so every existing
`from ..common.utils import load_config` keeps working unchanged.
"""

from __future__ import annotations

import logging
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def load_config() -> dict[str, Any]:
    """Load config from config.yaml."""
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    logger.debug("Configuration loaded successfully")
    return config
