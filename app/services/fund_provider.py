from __future__ import annotations

import importlib
from typing import Any

import fund as fund_module


def create_fund(*, reload_module: bool = False) -> Any:
    module = fund_module
    if reload_module:
        module = importlib.reload(fund_module)
    return module.MaYiFund()