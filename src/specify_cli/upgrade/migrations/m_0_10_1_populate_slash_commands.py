"""Migration: Populate missing slash commands from mission templates."""

from __future__ import annotations

from pathlib import Path

from specify_cli.agent_utils.directories import get_agent_dirs_for_project

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class PopulateSlashCommandsMigration(BaseMigration):
    """Populate agent command directories from mission templates if missing.

    Some v0.9.x projects initialized before proper template extraction
    may have empty agent command directories. This migration ensures
    all projects have slash commands available.

    This migration:
    1. Checks if agent command directories are empty or missing slash commands
    2. Finds mission command templates (software-dev or active mission)
    3. Copies templates to all agent directories with spec-kitty. prefix
    4. Handles all 12 supported agents
    """

    migration_id = "0.10.1_populate_slash_commands"
    description = "Populate missing slash commands from mission templates"
    target_version = "0.10.1"

    def detect(self, project_path: Path) -> bool:
        """Repair only command surfaces selected by the canonical agent config."""
        return any(len(list(path.glob("spec-kitty.*.md"))) < 8 for path in self._command_dirs(project_path))

    @staticmethod
    def _command_dirs(project_path: Path) -> list[Path]:
        """Match application eligibility without creating unconfigured roots."""
        return [project_path / root / subdir for root, subdir in get_agent_dirs_for_project(project_path) if (project_path / root).exists()]

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if we have mission templates to copy from."""
        # Check for mission templates
        missions_dir = project_path / ".kittify" / "missions"
        if not missions_dir.exists():
            return False, "No missions directory found"

        # Look for software-dev mission (most common)
        software_dev_templates = missions_dir / "software-dev" / "command-templates"
        if software_dev_templates.exists():
            return True, ""

        # Look for any mission with command-templates
        for mission_dir in missions_dir.iterdir():
            if mission_dir.is_dir():
                templates = mission_dir / "command-templates"
                if templates.exists():
                    return True, ""

        return False, "No mission command templates found"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Populate slash commands from mission templates."""
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        # Find mission templates
        missions_dir = project_path / ".kittify" / "missions"

        # Prefer software-dev, fallback to first available mission
        command_templates_dir = None
        software_dev_templates = missions_dir / "software-dev" / "command-templates"

        if software_dev_templates.exists():
            command_templates_dir = software_dev_templates
            mission_name = "software-dev"
        else:
            # Find first mission with templates
            for mission_dir in sorted(missions_dir.iterdir()):
                if mission_dir.is_dir():
                    templates = mission_dir / "command-templates"
                    if templates.exists():
                        command_templates_dir = templates
                        mission_name = mission_dir.name
                        break

        if not command_templates_dir:
            errors.append("No mission command templates found")
            return MigrationResult(
                success=False,
                changes_made=changes,
                errors=errors,
                warnings=warnings,
            )

        # Populate agent command directories (respecting user config)
        total_created = 0
        for agent_dir in self._command_dirs(project_path):
            created = self._populate_agent_commands(command_templates_dir, agent_dir, "md", dry_run, changes)
            if created > 0:
                agent_name = agent_dir.parent.name.lstrip(".")
                changes.append(f"Created {created} slash commands for {agent_name} from {mission_name}")
                total_created += created

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )

    def _populate_agent_commands(self, templates_dir: Path, output_dir: Path, extension: str, dry_run: bool, changes: list[str]) -> int:
        """Copy command templates to agent directory."""
        created_count = 0

        # Create directory if needed
        if not output_dir.exists():
            if dry_run:
                changes.append(f"Would create: {output_dir}")
            else:
                output_dir.mkdir(parents=True, exist_ok=True)
                changes.append(f"Created: {output_dir}")

        # Copy each template
        for template_path in sorted(templates_dir.glob("*.md")):
            filename = f"spec-kitty.{template_path.stem}.{extension}" if extension else f"spec-kitty.{template_path.stem}"
            dest_path = output_dir / filename

            # Skip if already exists
            if dest_path.exists():
                continue

            if dry_run:
                changes.append(f"Would create: {dest_path.name}")
            else:
                # Simple copy - no variable substitution needed for basic setup
                dest_path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
                changes.append(f"Created: {dest_path.name}")

            created_count += 1

        return created_count
