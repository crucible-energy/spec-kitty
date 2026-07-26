# Quickstart: Verify and Recover a Global Skill Projection

1. Inspect managed skill health:

   ```bash
   spec-kitty doctor skills --json
   ```

2. If an agent reports a skipped or missing generated skill, use the supported repair path rather than copying `SKILL.md` manually:

   ```bash
   spec-kitty agent config sync
   spec-kitty doctor skills --json
   ```

3. Restart or refresh the host so it reloads its discovery roots. Confirm the relevant package, for example `.agents/skills/spec-kitty-orchestrator-api-operator/SKILL.md`, exists.

4. Confirm that a user-authored neighboring skill was not changed. Generated projections are read-only compatibility artifacts; custom skills are user-owned.

Do not treat a current `agent-skills.lock` alone as proof of an integral projection. Use the mission's focused regression test for deterministic verification.
