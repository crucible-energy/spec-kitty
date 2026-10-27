"""Version identity stays exact without scanning distributions on every import."""

import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.integration]


def test_import_defers_distribution_scan_until_version_is_requested():
    env = os.environ.copy()
    env.pop("SPEC_KITTY_TEST_MODE", None)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import importlib.metadata as metadata
from unittest.mock import patch
with patch.object(metadata, 'packages_distributions', wraps=metadata.packages_distributions) as scan:
    import specify_cli
    assert scan.call_count == 0, scan.call_count
    assert '__version__' in dir(specify_cli)
    from specify_cli import __version__
    from specify_cli.version_utils import get_version
    assert isinstance(__version__, str)
    assert __version__ == get_version()
    assert scan.call_count == 1, scan.call_count
    assert specify_cli.__version__ is __version__
    assert scan.call_count == 1
    try:
        specify_cli.no_such_public_attribute
    except AttributeError:
        pass
    else:
        raise AssertionError('unknown public attribute must refuse')
""",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_test_version_override_remains_captured_at_import():
    env = os.environ.copy()
    env["SPEC_KITTY_TEST_MODE"] = "1"
    env["SPEC_KITTY_CLI_VERSION"] = "9.8.7-test"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import os
import specify_cli
os.environ['SPEC_KITTY_CLI_VERSION'] = '1.2.3-changed'
assert specify_cli.__version__ == '9.8.7-test'
import importlib
import specify_cli.version_utils as versions
os.environ.pop('SPEC_KITTY_TEST_MODE')
from unittest.mock import patch
with patch.object(versions, 'get_version', return_value='3.2.8-reloaded') as resolve:
    importlib.reload(specify_cli)
    assert resolve.call_count == 0
    assert specify_cli.__version__ == '3.2.8-reloaded'
    assert resolve.call_count == 1
""",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
