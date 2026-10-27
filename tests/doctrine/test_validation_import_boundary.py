"""Schema validation must stay strict without taxing unrelated doctrine reads."""

import subprocess
import sys


def test_repository_imports_do_not_initialize_unused_schema_engine():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from doctrine.service import DoctrineService; "
            "service = DoctrineService(); "
            "assert 'jsonschema' not in sys.modules; "
            "from doctrine.agent_profiles.validation import validate_agent_profile_yaml; "
            "assert validate_agent_profile_yaml({}); "
            "assert 'jsonschema' in sys.modules",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
