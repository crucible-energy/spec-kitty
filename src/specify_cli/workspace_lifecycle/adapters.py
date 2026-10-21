"""Creator-side authorities. Events and local ancestry never certify delivery."""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import time
from typing import cast

from specify_cli.workspace_lifecycle.policy import Identity
from specify_cli.workspace_lifecycle.state import StateError


class GitHubDelivery:
    """Fresh authenticated same-repository PR delivery to its default branch.

    A source SHA from a merged PR explicitly binds squash/rebase delivery without
    pretending the original commit must be an ancestor of the merge commit.
    This authority establishes delivery only, never owner release or fencing.
    """

    def __init__(self, *, timeout: float = 10.0) -> None:
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Delivery authority requires a finite positive timeout")
        self.timeout = timeout

    @staticmethod
    def _get(path: str, deadline: float) -> dict[str, object]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise StateError("Delivery authority unavailable")
        env = {k: v for k, v in os.environ.items() if k != "GH_DEBUG"}
        env["GH_PROMPT_DISABLED"] = "1"
        try:
            result = subprocess.run(
                ["gh", "api", "--hostname", "github.com", "--method", "GET", path],
                capture_output=True,
                check=False,
                timeout=remaining,
                env=env,
            )
            if result.returncode != 0 or len(result.stdout) > 4 * 1024 * 1024:
                raise StateError("Delivery authority unavailable")
            data: object = json.loads(result.stdout)
            if not isinstance(data, dict):
                raise StateError("Delivery authority unavailable")
            return cast(dict[str, object], data)
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            raise StateError("Delivery authority unavailable") from exc

    @staticmethod
    def _same_repository(value: object, expected: Identity) -> bool:
        return (
            isinstance(value, dict)
            and type(value.get("id")) is int
            and value.get("id") == expected.repository_id
            and isinstance(value.get("full_name"), str)
            and value["full_name"].lower() == expected.repository
        )

    def verify(self, expected: Identity, pr: int) -> str | None:
        """Return an exact accepted-PR identity or no delivery; fail on unavailable authority."""
        if type(pr) is not int or pr <= 0:
            raise ValueError("Positive PR number required")
        deadline = time.monotonic() + self.timeout
        repository = self._get(f"repos/{expected.repository}", deadline)
        if not self._same_repository(repository, expected):
            return None
        default_branch = repository.get("default_branch")
        if not isinstance(default_branch, str) or not default_branch:
            raise StateError("Delivery authority unavailable")
        pull = self._get(f"repos/{expected.repository}/pulls/{pr}", deadline)
        head, base = pull.get("head"), pull.get("base")
        merged_at, merge_sha = pull.get("merged_at"), pull.get("merge_commit_sha")
        if (
            type(pull.get("number")) is not int
            or pull.get("number") != pr
            or pull.get("merged") is not True
            or pull.get("state") != "closed"
            or not isinstance(merged_at, str)
            or not merged_at
            or not isinstance(merge_sha, str)
            or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", merge_sha)
            or not isinstance(head, dict)
            or head.get("sha") != expected.head
            or not self._same_repository(head.get("repo"), expected)
            or not isinstance(base, dict)
            or base.get("ref") != default_branch
            or not self._same_repository(base.get("repo"), expected)
        ):
            return None
        return f"github:{expected.repository_id}:pr:{pr}:merge:{merge_sha}"
