"""Pin local ingress and worker children to their generating distribution."""

from __future__ import annotations

import sys
from pathlib import Path


def distribution_argv(module: str, *arguments: str) -> list[str]:
    """Preserve exact module ownership across cwd and ambient module paths."""
    root = str(Path(__file__).resolve().parents[2])
    bootstrap = f"import runpy,sys; sys.path.insert(0,{root!r}); runpy.run_module({module!r},run_name='__main__')"
    return [str(Path(sys.executable).absolute()), "-I", "-c", bootstrap, *arguments]
