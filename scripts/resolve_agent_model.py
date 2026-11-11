#!/usr/bin/env python3
"""Resolve the configured model for one workflow role.

This is intentionally runner-agnostic: a shell wrapper can use the output to
configure any OpenAI-compatible CLI or SDK without putting credentials here.
"""

from __future__ import annotations

import argparse
import os
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".agents" / "models.toml"
ROLES = {"strategist", "researcher", "implementer", "reviewer", "integrator"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=sorted(ROLES))
    args = parser.parse_args()

    with CONFIG.open("rb") as handle:
        config = tomllib.load(handle)
    role_config = config["roles"][args.role]
    env_name = f"AGENT_{args.role.upper()}_MODEL"
    model = os.environ.get(env_name, role_config["model"])
    print(model)
    return 0


if __name__ == "__main__":
    sys.exit(main())
