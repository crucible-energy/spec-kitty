"""Authenticated accessible-repository inventory, with bounded pagination."""

from __future__ import annotations

import json
import math
import os
import subprocess
import time

from specify_cli.workspace_lifecycle.discovery import parse_repository_pages


class OrganizationInventoryUnavailable(RuntimeError):
    """No complete accessible-repository inventory was established."""


def fetch_repositories(organization: str, *, timeout: float = 30.0) -> dict[str, int]:
    """Use the configured GitHub credential without storing it or raw failures."""
    parse_repository_pages([], organization)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Inventory timeout must be positive and finite")
    deadline = time.monotonic() + timeout
    pages: list[object] = []
    env = {k: v for k, v in os.environ.items() if k != "GH_DEBUG"}
    env["GH_PROMPT_DISABLED"] = "1"
    try:
        for number in range(1, 101):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise OrganizationInventoryUnavailable("Organization inventory deadline exceeded")
            response = subprocess.run(
                [
                    "gh",
                    "api",
                    "--hostname",
                    "github.com",
                    "--method",
                    "GET",
                    f"orgs/{organization}/repos?type=all&sort=full_name&direction=asc&per_page=100&page={number}",
                ],
                capture_output=True,
                check=False,
                timeout=remaining,
                env=env,
            )
            if response.returncode != 0 or len(response.stdout) > 4 * 1024 * 1024:
                raise OrganizationInventoryUnavailable("Organization inventory request failed; check scoped GitHub access")
            page = json.loads(response.stdout)
            if not isinstance(page, list) or len(page) > 100:
                raise OrganizationInventoryUnavailable("Organization inventory response is invalid")
            pages.append(page)
            if len(page) < 100:
                return parse_repository_pages(pages, organization)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise OrganizationInventoryUnavailable("Organization inventory is unavailable or invalid") from exc
    raise OrganizationInventoryUnavailable("Organization inventory exceeds the bounded page count")
