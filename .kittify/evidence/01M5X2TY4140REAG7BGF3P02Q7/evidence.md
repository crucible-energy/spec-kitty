2026-10-26T21:43:06.3549842Z Current runner version: '2.338.0'
2026-10-26T21:43:06.3576470Z ##[group]Runner Image Provisioner
2026-10-26T21:43:06.3577352Z Hosted Compute Agent
2026-10-26T21:43:06.3578167Z Version: 20261021.618
2026-10-26T21:43:06.3578821Z Commit: 21505ad2541d5be6135ed84fc33697146cf75b8e
2026-10-26T21:43:06.3579578Z Build Date: 2026-10-21T00:45:21Z
2026-10-26T21:43:06.3580372Z Worker ID: {e3d60a9f-8551-47ec-8d1d-ba33be2f38d7}
2026-10-26T21:43:06.3581101Z Region: westcentralus
2026-10-26T21:43:06.3581734Z Cloud: Azure
2026-10-26T21:43:06.3582304Z ##[endgroup]
2026-10-26T21:43:06.3584795Z ##[group]Operating System
2026-10-26T21:43:06.3585592Z Ubuntu
2026-10-26T21:43:06.3586123Z 24.04.5
2026-10-26T21:43:06.3586732Z LTS
2026-10-26T21:43:06.3587268Z ##[endgroup]
2026-10-26T21:43:06.3587849Z ##[group]Runner Image
2026-10-26T21:43:06.3588533Z Image: ubuntu-24.04
2026-10-26T21:43:06.3589113Z Version: 20261012.334.1
2026-10-26T21:43:06.3590485Z Included Software: https://github.com/actions/runner-images/blob/ubuntu24/20261012.334/images/ubuntu/Ubuntu2404-Readme.md
2026-10-26T21:43:06.3592098Z Image Release: https://github.com/actions/runner-images/releases/tag/ubuntu24%2F20261012.334
2026-10-26T21:43:06.3593425Z ##[endgroup]
2026-10-26T21:43:06.3594554Z ##[group]GITHUB_TOKEN Permissions
2026-10-26T21:43:06.3596678Z Contents: read
2026-10-26T21:43:06.3597327Z Metadata: read
2026-10-26T21:43:06.3597992Z ##[endgroup]
2026-10-26T21:43:06.3600249Z Secret source: Actions
2026-10-26T21:43:06.3601234Z Cache mode: write
2026-10-26T21:43:06.3602099Z Prepare workflow directory
2026-10-26T21:43:06.3960687Z Prepare all required actions
2026-10-26T21:43:06.4009807Z Getting action download info
2026-10-26T21:43:06.7428721Z Download action repository 'actions/checkout@08c6903cd8c0fde910a37f88322edcfb5dd907a8' (SHA:08c6903cd8c0fde910a37f88322edcfb5dd907a8)
2026-10-26T21:43:06.8900128Z Download action repository 'astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d' (SHA:20cfd1bf945f4377ade1205e4dbc17946fc9a30d)
2026-10-26T21:43:07.7452253Z Download action repository 'actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a' (SHA:043fb46d1a93c77aae656e7c1c64a875d1fc6a0a)
2026-10-26T21:43:07.9339285Z Complete job name: architectural fast gates (ratchet/census, always-on)
2026-10-26T21:43:08.0321144Z ##[group]Run actions/checkout@08c6903cd8c0fde910a37f88322edcfb5dd907a8
2026-10-26T21:43:08.0322351Z with:
2026-10-26T21:43:08.0323066Z   fetch-depth: 0
2026-10-26T21:43:08.0323600Z   repository: crucible-energy/spec-kitty
2026-10-26T21:43:08.0328064Z   token: ***
2026-10-26T21:43:08.0328546Z   ssh-strict: true
2026-10-26T21:43:08.0329036Z   ssh-user: git
2026-10-26T21:43:08.0329528Z   persist-credentials: true
2026-10-26T21:43:08.0330080Z   clean: true
2026-10-26T21:43:08.0330573Z   sparse-checkout-cone-mode: true
2026-10-26T21:43:08.0331163Z   fetch-tags: false
2026-10-26T21:43:08.0331649Z   show-progress: true
2026-10-26T21:43:08.0332145Z   lfs: false
2026-10-26T21:43:08.0332766Z   submodules: false
2026-10-26T21:43:08.0333260Z   set-safe-directory: true
2026-10-26T21:43:08.0334191Z ##[endgroup]
2026-10-26T21:43:08.1468739Z Syncing repository: crucible-energy/spec-kitty
2026-10-26T21:43:08.1472201Z ##[group]Getting Git version info
2026-10-26T21:43:08.1474173Z Working directory is '/home/runner/work/spec-kitty/spec-kitty'
2026-10-26T21:43:08.1476323Z [command]/usr/bin/git version
2026-10-26T21:43:08.1569111Z git version 2.55.0
2026-10-26T21:43:08.1602351Z ##[endgroup]
2026-10-26T21:43:08.1611924Z Temporarily overriding HOME='/home/runner/work/_temp/ae49b438-2582-4b19-989b-6611b6557d0d' before making global git config changes
2026-10-26T21:43:08.1615744Z Adding repository directory to the temporary git global config as a safe directory
2026-10-26T21:43:08.1618574Z [command]/usr/bin/git config --global --add safe.directory /home/runner/work/spec-kitty/spec-kitty
2026-10-26T21:43:08.1680114Z Deleting the contents of '/home/runner/work/spec-kitty/spec-kitty'
2026-10-26T21:43:08.1687245Z ##[group]Initializing the repository
2026-10-26T21:43:08.1694270Z [command]/usr/bin/git init /home/runner/work/spec-kitty/spec-kitty
2026-10-26T21:43:08.1840498Z hint: Using 'master' as the name for the initial branch. This default branch name
2026-10-26T21:43:08.1844967Z hint: will change to "main" in Git 3.0. To configure the initial branch name
2026-10-26T21:43:08.1846833Z hint: to use in all of your new repositories, which will suppress this warning,
2026-10-26T21:43:08.1848413Z hint: call:
2026-10-26T21:43:08.1849410Z hint:
2026-10-26T21:43:08.1850428Z hint: 	git config --global init.defaultBranch <name>
2026-10-26T21:43:08.1851699Z hint:
2026-10-26T21:43:08.1853263Z hint: Names commonly chosen instead of 'master' are 'main', 'trunk' and
2026-10-26T21:43:08.1855196Z hint: 'development'. The just-created branch can be renamed via this command:
2026-10-26T21:43:08.1856742Z hint:
2026-10-26T21:43:08.1857592Z hint: 	git branch -m <name>
2026-10-26T21:43:08.1858521Z hint:
2026-10-26T21:43:08.1859834Z hint: Disable this message with "git config set advice.defaultBranchName false"
2026-10-26T21:43:08.1862196Z Initialized empty Git repository in /home/runner/work/spec-kitty/spec-kitty/.git/
2026-10-26T21:43:08.1866769Z [command]/usr/bin/git remote add origin https://github.com/crucible-energy/spec-kitty
2026-10-26T21:43:08.1925657Z ##[endgroup]
2026-10-26T21:43:08.1928012Z ##[group]Disabling automatic garbage collection
2026-10-26T21:43:08.1929740Z [command]/usr/bin/git config --local gc.auto 0
2026-10-26T21:43:08.1973743Z ##[endgroup]
2026-10-26T21:43:08.1975559Z ##[group]Setting up auth
2026-10-26T21:43:08.1981032Z [command]/usr/bin/git config --local --name-only --get-regexp core\.sshCommand
2026-10-26T21:43:08.2040400Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
2026-10-26T21:43:08.2459967Z [command]/usr/bin/git config --local --name-only --get-regexp http\.https\:\/\/github\.com\/\.extraheader
2026-10-26T21:43:08.2503282Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'http\.https\:\/\/github\.com\/\.extraheader' && git config --local --unset-all 'http.https://github.com/.extraheader' || :"
2026-10-26T21:43:08.2756607Z [command]/usr/bin/git config --local http.https://github.com/.extraheader AUTHORIZATION: basic ***
2026-10-26T21:43:08.2807035Z ##[endgroup]
2026-10-26T21:43:08.2808596Z ##[group]Fetching the repository
2026-10-26T21:43:08.2819409Z [command]/usr/bin/git -c protocol.version=2 fetch --prune --no-recurse-submodules origin +refs/heads/*:refs/remotes/origin/* +refs/tags/*:refs/tags/* +0d5539d16cfeaeef7644bba8775d99e3b44e1695:refs/remotes/pull/132/merge
2026-10-26T21:43:19.5048256Z From https://github.com/crucible-energy/spec-kitty
2026-10-26T21:43:19.5049928Z  * [new branch]          1.x-maintenance                          -> origin/1.x-maintenance
2026-10-26T21:43:19.5051876Z  * [new branch]          architecture/design-execution-layer      -> origin/architecture/design-execution-layer
2026-10-26T21:43:19.5054565Z  * [new branch]          automation/sonar-security-20260423       -> origin/automation/sonar-security-20260423
2026-10-26T21:43:19.5056530Z  * [new branch]          automation/sonar-security-20260424       -> origin/automation/sonar-security-20260424
2026-10-26T21:43:19.5058631Z  * [new branch]          automation/sonar-security-20260424-dashboard -> origin/automation/sonar-security-20260424-dashboard
2026-10-26T21:43:19.5060474Z  * [new branch]          automation/sonar-security-20260425       -> origin/automation/sonar-security-20260425
2026-10-26T21:43:19.5061934Z  * [new branch]          automation/sonar-security-20260426       -> origin/automation/sonar-security-20260426
2026-10-26T21:43:19.5064039Z  * [new branch]          automation/sonar-security-20260512-urllib3-sri -> origin/automation/sonar-security-20260512-urllib3-sri
2026-10-26T21:43:19.5066095Z  * [new branch]          automation/sonar-security-20260514-core-paths -> origin/automation/sonar-security-20260514-core-paths
2026-10-26T21:43:19.5068387Z  * [new branch]          automation/sonar-security-20260516-regex-dos -> origin/automation/sonar-security-20260516-regex-dos
2026-10-26T21:43:19.5070409Z  * [new branch]          automation/sonar-security-20260517-nightly-followup -> origin/automation/sonar-security-20260517-nightly-followup
2026-10-26T21:43:19.5071639Z  * [new branch]          automation/sonar-security-20260607-cli-cleanups -> origin/automation/sonar-security-20260607-cli-cleanups
2026-10-26T21:43:19.5073942Z  * [new branch]          automation/sonar-security-20260607-cli-cleanups-v2 -> origin/automation/sonar-security-20260607-cli-cleanups-v2
2026-10-26T21:43:19.5075198Z  * [new branch]          automation/sonar-security-20260619       -> origin/automation/sonar-security-20260619
2026-10-26T21:43:19.5076279Z  * [new branch]          automation/sonar-security-fixes-20260618 -> origin/automation/sonar-security-fixes-20260618
2026-10-26T21:43:19.5077451Z  * [new branch]          automation/sonar-security-followups-20260430-dashboard-xss -> origin/automation/sonar-security-followups-20260430-dashboard-xss
2026-10-26T21:43:19.5078651Z  * [new branch]          automation/sonar-security-tranche-a-20260429 -> origin/automation/sonar-security-tranche-a-20260429
2026-10-26T21:43:19.5079719Z  * [new branch]          automation/sonarcloud-security-loopback-localhost -> origin/automation/sonarcloud-security-loopback-localhost
2026-10-26T21:43:19.5081042Z  * [new branch]          automation/spec-kitty-sonarcloud-and-security-issues -> origin/automation/spec-kitty-sonarcloud-and-security-issues
2026-10-26T21:43:19.5082726Z  * [new branch]          automation/spec-kitty-sonarcloud-and-security-issues-20260528 -> origin/automation/spec-kitty-sonarcloud-and-security-issues-20260528
2026-10-26T21:43:19.5084442Z  * [new branch]          automation/spec-kitty-sonarcloud-and-security-issues-20260530 -> origin/automation/spec-kitty-sonarcloud-and-security-issues-20260530
2026-10-26T21:43:19.5086991Z  * [new branch]          automation/spec-kitty-sonarcloud-and-security-issues-20260531 -> origin/automation/spec-kitty-sonarcloud-and-security-issues-20260531
2026-10-26T21:43:19.5176731Z  * [new branch]          automation/spec-kitty-sonarcloud-and-security-issues-20260612 -> origin/automation/spec-kitty-sonarcloud-and-security-issues-20260612
2026-10-26T21:43:19.5178736Z  * [new branch]          automation/spec-kitty-sonarcloud-and-security-issues-20260621 -> origin/automation/spec-kitty-sonarcloud-and-security-issues-20260621
2026-10-26T21:43:19.5180069Z  * [new branch]          automation/spec-kitty-sonarcloud-security-20260519 -> origin/automation/spec-kitty-sonarcloud-security-20260519
2026-10-26T21:43:19.5181191Z  * [new branch]          automation/spec-kitty-sonarcloud-security-20260531 -> origin/automation/spec-kitty-sonarcloud-security-20260531
2026-10-26T21:43:19.5183145Z  * [new branch]          automation/spec-kitty-sonarcloud-security-20260603 -> origin/automation/spec-kitty-sonarcloud-security-20260603
2026-10-26T21:43:19.5184979Z  * [new branch]          automation/spec-kitty-sonarcloud-security-hook-fd-write -> origin/automation/spec-kitty-sonarcloud-security-hook-fd-write
2026-10-26T21:43:19.5186435Z  * [new branch]          automation/spec-kitty-sonarcloud-security-hook-registrar-fix -> origin/automation/spec-kitty-sonarcloud-security-hook-registrar-fix
2026-10-26T21:43:19.5187784Z  * [new branch]          automation/spec-kitty-sonarcloud-security-issues -> origin/automation/spec-kitty-sonarcloud-security-issues
2026-10-26T21:43:19.5188660Z  * [new branch]          base/pre-075                             -> origin/base/pre-075
2026-10-26T21:43:19.5189513Z  * [new branch]          beta-sync-remediation-adaptive-batching  -> origin/beta-sync-remediation-adaptive-batching
2026-10-26T21:43:19.5190608Z  * [new branch]          chore/tend-320-rc-changelog              -> origin/chore/tend-320-rc-changelog
2026-10-26T21:43:19.5191579Z  * [new branch]          claude/doctrine-bundle-spec-kitty-7Z1kR  -> origin/claude/doctrine-bundle-spec-kitty-7Z1kR
2026-10-26T21:43:19.5193036Z  * [new branch]          codex/fix-1116-top-level-tasks-mission   -> origin/codex/fix-1116-top-level-tasks-mission
2026-10-26T21:43:19.5195110Z  * [new branch]          codex/fix-1128-doctrine-security-hardening -> origin/codex/fix-1128-doctrine-security-hardening
2026-10-26T21:43:19.5197057Z  * [new branch]          codex/fix-1145-decision-open-json-contract -> origin/codex/fix-1145-decision-open-json-contract
2026-10-26T21:43:19.5198836Z  * [new branch]          codex/fix-385-release-installability-gate -> origin/codex/fix-385-release-installability-gate
2026-10-26T21:43:19.5200681Z  * [new branch]          codex/fix-dashboard-glossary-shell-1179  -> origin/codex/fix-dashboard-glossary-shell-1179
2026-10-26T21:43:19.5202634Z  * [new branch]          codex/fix-grep-absence-self-match-1147   -> origin/codex/fix-grep-absence-self-match-1147
2026-10-26T21:43:19.5204341Z  * [new branch]          codex/fix-legacy-path-audit-1134         -> origin/codex/fix-legacy-path-audit-1134
2026-10-26T21:43:19.5206155Z  * [new branch]          codex/fix-mission-081-review-findings    -> origin/codex/fix-mission-081-review-findings
2026-10-26T21:43:19.5208068Z  * [new branch]          codex/improve-review-override-ux-1148    -> origin/codex/improve-review-override-ux-1148
2026-10-26T21:43:19.5209623Z  * [new branch]          codex/issue-127-agent-migration          -> origin/codex/issue-127-agent-migration
2026-10-26T21:43:19.5211055Z  * [new branch]          codex/issue-1623-doctor-health-render    -> origin/codex/issue-1623-doctor-health-render
2026-10-26T21:43:19.5212714Z  * [new branch]          codex/issue-1824-dashboard-coord         -> origin/codex/issue-1824-dashboard-coord
2026-10-26T21:43:19.5214266Z  * [new branch]          codex/materialize-retrospective-events-1183 -> origin/codex/materialize-retrospective-events-1183
2026-10-26T21:43:19.5215759Z  * [new branch]          codex/native-local-validation            -> origin/codex/native-local-validation
2026-10-26T21:43:19.5217573Z  * [new branch]          codex/organization-workspace-lifecycle-20261020 -> origin/codex/organization-workspace-lifecycle-20261020
2026-10-26T21:43:19.5218748Z  * [new branch]          codex/owned-lanes-analysis               -> origin/codex/owned-lanes-analysis
2026-10-26T21:43:19.5219629Z  * [new branch]          codex/owned-op-worktree-routing-20261020 -> origin/codex/owned-op-worktree-routing-20261020
2026-10-26T21:43:19.5220521Z  * [new branch]          codex/pre-review-aggregate-budget        -> origin/codex/pre-review-aggregate-budget
2026-10-26T21:43:19.5221419Z  * [new branch]          codex/remove-standalone-governance-verbs -> origin/codex/remove-standalone-governance-verbs
2026-10-26T21:43:19.5222952Z  * [new branch]          codex/spec-kitty-sonarcloud-and-security-issues-20260617-0907 -> origin/codex/spec-kitty-sonarcloud-and-security-issues-20260617-0907
2026-10-26T21:43:19.5224275Z  * [new branch]          codex/spec-kitty-sonarcloud-and-security-issues-20260618-0912 -> origin/codex/spec-kitty-sonarcloud-and-security-issues-20260618-0912
2026-10-26T21:43:19.5225434Z  * [new branch]          codex/spec-kitty-sonarcloud-security-20260519 -> origin/codex/spec-kitty-sonarcloud-security-20260519
2026-10-26T21:43:19.5227200Z  * [new branch]          codex/spec-kitty-sonarcloud-security-20260530 -> origin/codex/spec-kitty-sonarcloud-security-20260530
2026-10-26T21:43:19.5228760Z  * [new branch]          codex/spec-kitty-sonarcloud-security-20260619 -> origin/codex/spec-kitty-sonarcloud-security-20260619
2026-10-26T21:43:19.5229781Z  * [new branch]          codex/spec-kitty-sonarcloud-security-20260620 -> origin/codex/spec-kitty-sonarcloud-security-20260620
2026-10-26T21:43:19.5230702Z  * [new branch]          codex/top-level-empty-groups-help        -> origin/codex/top-level-empty-groups-help
2026-10-26T21:43:19.5231490Z  * [new branch]          design/degod-tasks-2116                  -> origin/design/degod-tasks-2116
2026-10-26T21:43:19.5232212Z  * [new branch]          docs-fixes-2026-04-10                    -> origin/docs-fixes-2026-04-10
2026-10-26T21:43:19.5233611Z  * [new branch]          docs/branch-intent-governance-upgrade    -> origin/docs/branch-intent-governance-upgrade
2026-10-26T21:43:19.5234490Z  * [new branch]          docs/orchestrator-github-install         -> origin/docs/orchestrator-github-install
2026-10-26T21:43:19.5235369Z  * [new branch]          docs/prefer-pipx-installation-1012       -> origin/docs/prefer-pipx-installation-1012
2026-10-26T21:43:19.5236261Z  * [new branch]          docs/spec-kitty-host-skill-trace         -> origin/docs/spec-kitty-host-skill-trace
2026-10-26T21:43:19.5237170Z  * [new branch]          doctrine/semantic-compression-randy-reducer -> origin/doctrine/semantic-compression-randy-reducer
2026-10-26T21:43:19.5238015Z  * [new branch]          feat/2262-import-history                 -> origin/feat/2262-import-history
2026-10-26T21:43:19.5238759Z  * [new branch]          feat/agent-upgrade-prompts               -> origin/feat/agent-upgrade-prompts
2026-10-26T21:43:19.5239536Z  * [new branch]          feat/decision-moment-v1-cli              -> origin/feat/decision-moment-v1-cli
2026-10-26T21:43:19.5240339Z  * [new branch]          feat/docs-ia-onboarding-overhaul         -> origin/feat/docs-ia-onboarding-overhaul
2026-10-26T21:43:19.5241108Z  * [new branch]          feat/org-doctrine-layer                  -> origin/feat/org-doctrine-layer
2026-10-26T21:43:19.5241953Z  * [new branch]          feat/phase-3-charter-synthesizer-pipeline -> origin/feat/phase-3-charter-synthesizer-pipeline
2026-10-26T21:43:19.5243176Z  * [new branch]          feat/single-mission-surface-resolver     -> origin/feat/single-mission-surface-resolver
2026-10-26T21:43:19.5243978Z  * [new branch]          feat/templates-as-config                 -> origin/feat/templates-as-config
2026-10-26T21:43:19.5244710Z  * [new branch]          feature/711-mutant-slaying               -> origin/feature/711-mutant-slaying
2026-10-26T21:43:19.5245526Z  * [new branch]          feature/metadata-state-type-hardening    -> origin/feature/metadata-state-type-hardening
2026-10-26T21:43:19.5246404Z  * [new branch]          fix-1420-grep-negative-invariants        -> origin/fix-1420-grep-negative-invariants
2026-10-26T21:43:19.5247405Z  * [new branch]          fix-1464-activation-include-contract     -> origin/fix-1464-activation-include-contract
2026-10-26T21:43:19.5248293Z  * [new branch]          fix/1149-accept-commit-meta-clean        -> origin/fix/1149-accept-commit-meta-clean
2026-10-26T21:43:19.5249078Z  * [new branch]          fix/1149-accept-diagnostics              -> origin/fix/1149-accept-diagnostics
2026-10-26T21:43:19.5249991Z  * [new branch]          fix/1188-wp-status-changed-envelope-duplication -> origin/fix/1188-wp-status-changed-envelope-duplication
2026-10-26T21:43:19.5251177Z  * [new branch]          fix/1199-1202-mission-type-required-fields-and-error-renderer -> origin/fix/1199-1202-mission-type-required-fields-and-error-renderer
2026-10-26T21:43:19.5252326Z  * [new branch]          fix/1203-mask1-emit-wp-created-schema-alignment -> origin/fix/1203-mask1-emit-wp-created-schema-alignment
2026-10-26T21:43:19.5253545Z  * [new branch]          fix/1440-status-json-utf8-drift          -> origin/fix/1440-status-json-utf8-drift
2026-10-26T21:43:19.5254491Z  * [new branch]          fix/1847-transactional-read-deleted-coord-branch -> origin/fix/1847-transactional-read-deleted-coord-branch
2026-10-26T21:43:19.5255481Z  * [new branch]          fix/1872-dedupe-skipped-migration-records -> origin/fix/1872-dedupe-skipped-migration-records
2026-10-26T21:43:19.5256375Z  * [new branch]          fix/1874-stale-agent-workflow-command    -> origin/fix/1874-stale-agent-workflow-command
2026-10-26T21:43:19.5257190Z  * [new branch]          fix/1891-json-output-hygiene             -> origin/fix/1891-json-output-hygiene
2026-10-26T21:43:19.5257924Z  * [new branch]          fix/2665-sync-remediation                -> origin/fix/2665-sync-remediation
2026-10-26T21:43:19.5258641Z  * [new branch]          fix/2804-2876-p0-repros                  -> origin/fix/2804-2876-p0-repros
2026-10-26T21:43:19.5259546Z  * [new branch]          fix/2883-reconciler-followups            -> origin/fix/2883-reconciler-followups
2026-10-26T21:43:19.5260318Z  * [new branch]          fix/783-bold-inline-subtasks             -> origin/fix/783-bold-inline-subtasks
2026-10-26T21:43:19.5261109Z  * [new branch]          fix/accept-coord-artifact-checks         -> origin/fix/accept-coord-artifact-checks
2026-10-26T21:43:19.5261989Z  * [new branch]          fix/agent-upgrade-check-once-per-session -> origin/fix/agent-upgrade-check-once-per-session
2026-10-26T21:43:19.5263235Z  * [new branch]          fix/arch-gate-allow-full-ci-block-labels -> origin/fix/arch-gate-allow-full-ci-block-labels
2026-10-26T21:43:19.5264098Z  * [new branch]          fix/audit-non-object-json-1425           -> origin/fix/audit-non-object-json-1425
2026-10-26T21:43:19.5264877Z  * [new branch]          fix/charter-e2e-827-tranche-2            -> origin/fix/charter-e2e-827-tranche-2
2026-10-26T21:43:19.5265676Z  * [new branch]          fix/charter-p7-release-closure           -> origin/fix/charter-p7-release-closure
2026-10-26T21:43:19.5266461Z  * [new branch]          fix/d5-sync-target-authority             -> origin/fix/d5-sync-target-authority
2026-10-26T21:43:19.5267257Z  * [new branch]          fix/deny-by-default-sync-consent         -> origin/fix/deny-by-default-sync-consent
2026-10-26T21:43:19.5268157Z  * [new branch]          fix/finalize-tasks-coord-branch-commit-1653 -> origin/fix/finalize-tasks-coord-branch-commit-1653
2026-10-26T21:43:19.5269101Z  * [new branch]          fix/global-skill-projection-integrity    -> origin/fix/global-skill-projection-integrity
2026-10-26T21:43:19.5269983Z  * [new branch]          fix/implement-review-loop-recovery       -> origin/fix/implement-review-loop-recovery
2026-10-26T21:43:19.5270891Z  * [new branch]          fix/issue-1413-managed-lane-sparse-checkout -> origin/fix/issue-1413-managed-lane-sparse-checkout
2026-10-26T21:43:19.5271786Z  * [new branch]          fix/issue-1433-step-contract-inputs      -> origin/fix/issue-1433-step-contract-inputs
2026-10-26T21:43:19.5273066Z  * [new branch]          fix/issue-1448-acceptance-lane-blockers  -> origin/fix/issue-1448-acceptance-lane-blockers
2026-10-26T21:43:19.5273989Z  * [new branch]          fix/issue-1459-charter-lint-checks-shim  -> origin/fix/issue-1459-charter-lint-checks-shim
2026-10-26T21:43:19.5274897Z  * [new branch]          fix/issue-1462-check-prerequisites-alias -> origin/fix/issue-1462-check-prerequisites-alias
2026-10-26T21:43:19.5275789Z  * [new branch]          fix/issue-1468-agent-profile-readme-ids  -> origin/fix/issue-1468-agent-profile-readme-ids
2026-10-26T21:43:19.5276709Z  * [new branch]          fix/issue-1469-agent-profile-schema-version -> origin/fix/issue-1469-agent-profile-schema-version
2026-10-26T21:43:19.5277626Z  * [new branch]          fix/legacy-wpstatus-migration-current    -> origin/fix/legacy-wpstatus-migration-current
2026-10-26T21:43:19.5278450Z  * [new branch]          fix/loosen-python-version                -> origin/fix/loosen-python-version
2026-10-26T21:43:19.5279215Z  * [new branch]          fix/main-e2e-cross-cutting-ci            -> origin/fix/main-e2e-cross-cutting-ci
2026-10-26T21:43:19.5280048Z  * [new branch]          fix/manifest-self-hash-built-in-only     -> origin/fix/manifest-self-hash-built-in-only
2026-10-26T21:43:19.5280877Z  * [new branch]          fix/merge-lock-and-retry-safety          -> origin/fix/merge-lock-and-retry-safety
2026-10-26T21:43:19.5281785Z  * [new branch]          fix/orchestrator-review-result-contract  -> origin/fix/orchestrator-review-result-contract
2026-10-26T21:43:19.5282934Z  * [new branch]          fix/owned-analysis-implementation        -> origin/fix/owned-analysis-implementation
2026-10-26T21:43:19.5283759Z  * [new branch]          fix/owned-checkout-charter-root          -> origin/fix/owned-checkout-charter-root
2026-10-26T21:43:19.5284696Z  * [new branch]          fix/pr-collapse-generated-spec-kitty-artifacts -> origin/fix/pr-collapse-generated-spec-kitty-artifacts
2026-10-26T21:43:19.5285798Z  * [new branch]          fix/pr1205-post-merge-ci                 -> origin/fix/pr1205-post-merge-ci
2026-10-26T21:43:19.5286595Z  * [new branch]          fix/rc35-migration-target-ceiling        -> origin/fix/rc35-migration-target-ceiling
2026-10-26T21:43:19.5287427Z  * [new branch]          fix/rc35-migration-target-ci-guard       -> origin/fix/rc35-migration-target-ci-guard
2026-10-26T21:43:19.5288195Z  * [new branch]          fix/readme-wall-of-text                  -> origin/fix/readme-wall-of-text
2026-10-26T21:43:19.5289106Z  * [new branch]          fix/red-handling-policy-and-drg-regression-marks -> origin/fix/red-handling-policy-and-drg-regression-marks
2026-10-26T21:43:19.5290055Z  * [new branch]          fix/retrospective-yaml-whitespace        -> origin/fix/retrospective-yaml-whitespace
2026-10-26T21:43:19.5290891Z  * [new branch]          fix/review-independence-1579-1582        -> origin/fix/review-independence-1579-1582
2026-10-26T21:43:19.5291733Z  * [new branch]          fix/review-thread-closure-upstream       -> origin/fix/review-thread-closure-upstream
2026-10-26T21:43:19.5292941Z  * [new branch]          fix/runtime-next-result-default-docs-1456 -> origin/fix/runtime-next-result-default-docs-1456
2026-10-26T21:43:19.5293848Z  * [new branch]          fix/setup-plan-coord-worktree-1954       -> origin/fix/setup-plan-coord-worktree-1954
2026-10-26T21:43:19.5294677Z  * [new branch]          fix/stale-workspace-reproduction         -> origin/fix/stale-workspace-reproduction
2026-10-26T21:43:19.5295478Z  * [new branch]          fix/sync-migrate-cleanup-2665            -> origin/fix/sync-migrate-cleanup-2665
2026-10-26T21:43:19.5296431Z  * [new branch]          fix/sync-now-strict-exit-test-respects-m7-recovery -> origin/fix/sync-now-strict-exit-test-respects-m7-recovery
2026-10-26T21:43:19.5297444Z  * [new branch]          fix/teamspace-historical-evidence-dry-run -> origin/fix/teamspace-historical-evidence-dry-run
2026-10-26T21:43:19.5298420Z  * [new branch]          fix/teamspace-mission-state-closeout-guards -> origin/fix/teamspace-mission-state-closeout-guards
2026-10-26T21:43:19.5299509Z  * [new branch]          fix/teamspace-mission-state-upgrade-gate -> origin/fix/teamspace-mission-state-upgrade-gate
2026-10-26T21:43:19.5300323Z  * [new branch]          fix/uv-sources-events                    -> origin/fix/uv-sources-events
2026-10-26T21:43:19.5301022Z  * [new branch]          fix/uv-tool-rc-upgrade                   -> origin/fix/uv-tool-rc-upgrade
2026-10-26T21:43:19.5301743Z  * [new branch]          fixup/tech_debt_remediation              -> origin/fixup/tech_debt_remediation
2026-10-26T21:43:19.5302772Z  * [new branch]          glossary/branch-context-terms            -> origin/glossary/branch-context-terms
2026-10-26T21:43:19.5303625Z  * [new branch]          hotfix/3.1.10-click-runtime-dependency   -> origin/hotfix/3.1.10-click-runtime-dependency
2026-10-26T21:43:19.5304490Z  * [new branch]          issue-1438-model-task-routing-parity     -> origin/issue-1438-model-task-routing-parity
2026-10-26T21:43:19.5305524Z  * [new branch]          kitty/mission-canonical-producer-lint-01KS4XX4-clean -> origin/kitty/mission-canonical-producer-lint-01KS4XX4-clean
2026-10-26T21:43:19.5306904Z  * [new branch]          kitty/mission-cli-decision-moment-widen-mode-readiness-01KRC12S-lane-a -> origin/kitty/mission-cli-decision-moment-widen-mode-readiness-01KRC12S-lane-a
2026-10-26T21:43:19.5308248Z  * [new branch]          kitty/mission-identity-boundary-canary-ci-gate-01KS4XWV -> origin/kitty/mission-identity-boundary-canary-ci-gate-01KS4XWV
2026-10-26T21:43:19.5309504Z  * [new branch]          kitty/mission-identity-boundary-ci-gate-rerun-01KS51YK-lane-a -> origin/kitty/mission-identity-boundary-ci-gate-rerun-01KS51YK-lane-a
2026-10-26T21:43:19.5310845Z  * [new branch]          kitty/mission-logged-out-teamspace-cli-recovery-01KRC6CY-lane-a -> origin/kitty/mission-logged-out-teamspace-cli-recovery-01KRC6CY-lane-a
2026-10-26T21:43:19.5312314Z  * [new branch]          kitty/mission-migration-shim-ownership-rules-01KPDYDW -> origin/kitty/mission-migration-shim-ownership-rules-01KPDYDW
2026-10-26T21:43:19.5313887Z  * [new branch]          kitty/mission-mission-state-migration-determinism-cleanup-01KRC7JG -> origin/kitty/mission-mission-state-migration-determinism-cleanup-01KRC7JG
2026-10-26T21:43:19.5315391Z  * [new branch]          kitty/mission-mission-state-migration-determinism-cleanup-01KRC7JG-lane-b -> origin/kitty/mission-mission-state-migration-determinism-cleanup-01KRC7JG-lane-b
2026-10-26T21:43:19.5316838Z  * [new branch]          kitty/mission-offline-queue-enqueue-performance-01KRC4HN-lane-a -> origin/kitty/mission-offline-queue-enqueue-performance-01KRC4HN-lane-a
2026-10-26T21:43:19.5318436Z  * [new branch]          kitty/mission-sync-rejection-classification-and-queue-retry-hygiene-01KRC3TV-lane-a -> origin/kitty/mission-sync-rejection-classification-and-queue-retry-hygiene-01KRC3TV-lane-a
2026-10-26T21:43:19.5320145Z  * [new branch]          kitty/mission-test-stabilization-pre-existing-cluster-fix-01KT396S-planning -> origin/kitty/mission-test-stabilization-pre-existing-cluster-fix-01KT396S-planning
2026-10-26T21:43:19.5321690Z  * [new branch]          kitty/pr/agent-harness-install-audit-follow-through-01KT5YTQ-to-main -> origin/kitty/pr/agent-harness-install-audit-follow-through-01KT5YTQ-to-main
2026-10-26T21:43:19.5323314Z  * [new branch]          kitty/pr/mission-execution-context-unification-01KT3YBD-to-main -> origin/kitty/pr/mission-execution-context-unification-01KT3YBD-to-main
2026-10-26T21:43:19.5324542Z  * [new branch]          kitty/pr/pi-and-letta-agent-support-01KT4Q26-to-main -> origin/kitty/pr/pi-and-letta-agent-support-01KT4Q26-to-main
2026-10-26T21:43:19.5325718Z  * [new branch]          kitty/pr/release-320-workflow-reliability-01KQKV85-to-main -> origin/kitty/pr/release-320-workflow-reliability-01KQKV85-to-main
2026-10-26T21:43:19.5327015Z  * [new branch]          kitty/pr/unblock-sync-identity-boundary-canary-01KRZJ07-to-main -> origin/kitty/pr/unblock-sync-identity-boundary-canary-01KRZJ07-to-main
2026-10-26T21:43:19.5327941Z  * [new branch]          main                                     -> origin/main
2026-10-26T21:43:19.5328887Z  * [new branch]          mission/identity-boundary-ci-gate-rerun  -> origin/mission/identity-boundary-ci-gate-rerun
2026-10-26T21:43:19.5329786Z  * [new branch]          mission/wp-lane-state-machine-fsm        -> origin/mission/wp-lane-state-machine-fsm
2026-10-26T21:43:19.5330514Z  * [new branch]          pr-2030-rebase                           -> origin/pr-2030-rebase
2026-10-26T21:43:19.5331430Z  * [new branch]          pr/129-plan-concern-vocabulary-and-wp-traceability -> origin/pr/129-plan-concern-vocabulary-and-wp-traceability
2026-10-26T21:43:19.5332728Z  * [new branch]          pr/2169-cmd-output-file-leak-guard       -> origin/pr/2169-cmd-output-file-leak-guard
2026-10-26T21:43:19.5333811Z  * [new branch]          pr/2264-saas-sync-honesty                -> origin/pr/2264-saas-sync-honesty
2026-10-26T21:43:19.5334701Z  * [new branch]          pr/2419-compat-planner-contract-ci-portable -> origin/pr/2419-compat-planner-contract-ci-portable
2026-10-26T21:43:19.5335545Z  * [new branch]          pr/add-pr-workflow-rule                  -> origin/pr/add-pr-workflow-rule
2026-10-26T21:43:19.5336441Z  * [new branch]          pr/charter-doctrine-mission-type-configuration -> origin/pr/charter-doctrine-mission-type-configuration
2026-10-26T21:43:19.5337486Z  * [new branch]          pr/coordination-topology-stabilization-01KTZVQ2 -> origin/pr/coordination-topology-stabilization-01KTZVQ2
2026-10-26T21:43:19.5338396Z  * [new branch]          pr/op-record-commit-hint-1783            -> origin/pr/op-record-commit-hint-1783
2026-10-26T21:43:19.5339148Z  * [new branch]          pr/op-records-pr1869-1870                -> origin/pr/op-records-pr1869-1870
2026-10-26T21:43:19.5339931Z  * [new branch]          pr/refactor-1993-resolve-lanes-dir       -> origin/pr/refactor-1993-resolve-lanes-dir
2026-10-26T21:43:19.5340912Z  * [new branch]          pr/ruff-mypy-zero-errors                 -> origin/pr/ruff-mypy-zero-errors
2026-10-26T21:43:19.5341708Z  * [new branch]          pr/runtime-state-corpus-cutover          -> origin/pr/runtime-state-corpus-cutover
2026-10-26T21:43:19.5342867Z  * [new branch]          pr/session-presence-multi-harness        -> origin/pr/session-presence-multi-harness
2026-10-26T21:43:19.5343686Z  * [new branch]          pr/tool-gated-routing-1785               -> origin/pr/tool-gated-routing-1785
2026-10-26T21:43:19.5344435Z  * [new branch]          pr/tool-surface-contract                 -> origin/pr/tool-surface-contract
2026-10-26T21:43:19.5345119Z  * [new branch]          pr632-refresh                            -> origin/pr632-refresh
2026-10-26T21:43:19.5345907Z  * [new branch]          preformalize-tool-surface-glossary       -> origin/preformalize-tool-surface-glossary
2026-10-26T21:43:19.5346954Z  * [new branch]          refactor/quality-p4-doc-analysis-acceptance-packages -> origin/refactor/quality-p4-doc-analysis-acceptance-packages
2026-10-26T21:43:19.5347842Z  * [new branch]          release/3.1.7                            -> origin/release/3.1.7
2026-10-26T21:43:19.5348519Z  * [new branch]          release/3.2.0a5-tranche-1                -> origin/release/3.2.0a5-tranche-1
2026-10-26T21:43:19.5349241Z  * [new branch]          release/3.2.0a6-tranche-2                -> origin/release/3.2.0a6-tranche-2
2026-10-26T21:43:19.5349919Z  * [new branch]          release/3.2.0rc23                        -> origin/release/3.2.0rc23
2026-10-26T21:43:19.5350553Z  * [new branch]          release/v3.1.8                           -> origin/release/v3.1.8
2026-10-26T21:43:19.5351289Z  * [new branch]          remove-saas-sync-rollout-gate            -> origin/remove-saas-sync-rollout-gate
2026-10-26T21:43:19.5352053Z  * [new branch]          remove/spk-integrate-ci                  -> origin/remove/spk-integrate-ci
2026-10-26T21:43:19.5353132Z  * [new branch]          repair/teamspace-mission-state-history   -> origin/repair/teamspace-mission-state-history
2026-10-26T21:43:19.5354192Z  * [new branch]          research/tersifier-prose-compression     -> origin/research/tersifier-prose-compression
2026-10-26T21:43:19.5355471Z  * [new branch]          revert-2019-codex/spec-kitty-sonarcloud-and-security-issues-20260617-0907 -> origin/revert-2019-codex/spec-kitty-sonarcloud-and-security-issues-20260617-0907
2026-10-26T21:43:19.5356542Z  * [new branch]          revert/mission-129                       -> origin/revert/mission-129
2026-10-26T21:43:19.5357302Z  * [new branch]          review/direct-main-552ab1e-fixes         -> origin/review/direct-main-552ab1e-fixes
2026-10-26T21:43:19.5358160Z  * [new branch]          robert/1119-config-workflow-fixes        -> origin/robert/1119-config-workflow-fixes
2026-10-26T21:43:19.5358941Z  * [new branch]          robertDouglass-patch-1                   -> origin/robertDouglass-patch-1
2026-10-26T21:43:19.5359822Z  * [new branch]          ship/charter-synthesizer-phase3-completion -> origin/ship/charter-synthesizer-phase3-completion
2026-10-26T21:43:19.5360656Z  * [new branch]          spk-skill-pack-320                       -> origin/spk-skill-pack-320
2026-10-26T21:43:19.5361389Z  * [new branch]          trim-obsolete-cli-commands               -> origin/trim-obsolete-cli-commands
2026-10-26T21:43:19.5362194Z  * [new branch]          wp6-step-contract-executor-501           -> origin/wp6-step-contract-executor-501
2026-10-26T21:43:19.5363259Z  * [new tag]             crossrepo-bugfix-pack-2026-02-24         -> crossrepo-bugfix-pack-2026-02-24
2026-10-26T21:43:19.5363982Z  * [new tag]             saas-hardening-2026-02-24                -> saas-hardening-2026-02-24
2026-10-26T21:43:19.5364574Z  * [new tag]             v0.0.1                                   -> v0.0.1
2026-10-26T21:43:19.5365087Z  * [new tag]             v0.0.10                                  -> v0.0.10
2026-10-26T21:43:19.5365599Z  * [new tag]             v0.0.11                                  -> v0.0.11
2026-10-26T21:43:19.5366282Z  * [new tag]             v0.0.12                                  -> v0.0.12
2026-10-26T21:43:19.5366791Z  * [new tag]             v0.0.13                                  -> v0.0.13
2026-10-26T21:43:19.5367294Z  * [new tag]             v0.0.14                                  -> v0.0.14
2026-10-26T21:43:19.5367787Z  * [new tag]             v0.0.15                                  -> v0.0.15
2026-10-26T21:43:19.5368282Z  * [new tag]             v0.0.16                                  -> v0.0.16
2026-10-26T21:43:19.5368777Z  * [new tag]             v0.0.17                                  -> v0.0.17
2026-10-26T21:43:19.5369271Z  * [new tag]             v0.0.18                                  -> v0.0.18
2026-10-26T21:43:19.5369763Z  * [new tag]             v0.0.19                                  -> v0.0.19
2026-10-26T21:43:19.5370261Z  * [new tag]             v0.0.2                                   -> v0.0.2
2026-10-26T21:43:19.5370769Z  * [new tag]             v0.0.20                                  -> v0.0.20
2026-10-26T21:43:19.5371274Z  * [new tag]             v0.0.21                                  -> v0.0.21
2026-10-26T21:43:19.5371774Z  * [new tag]             v0.0.22                                  -> v0.0.22
2026-10-26T21:43:19.5372266Z  * [new tag]             v0.0.23                                  -> v0.0.23
2026-10-26T21:43:19.5373087Z  * [new tag]             v0.0.24                                  -> v0.0.24
2026-10-26T21:43:19.5373592Z  * [new tag]             v0.0.25                                  -> v0.0.25
2026-10-26T21:43:19.5374093Z  * [new tag]             v0.0.26                                  -> v0.0.26
2026-10-26T21:43:19.5374588Z  * [new tag]             v0.0.27                                  -> v0.0.27
2026-10-26T21:43:19.5375080Z  * [new tag]             v0.0.28                                  -> v0.0.28
2026-10-26T21:43:19.5375577Z  * [new tag]             v0.0.29                                  -> v0.0.29
2026-10-26T21:43:19.5376091Z  * [new tag]             v0.0.3                                   -> v0.0.3
2026-10-26T21:43:19.5376723Z  * [new tag]             v0.0.30                                  -> v0.0.30
2026-10-26T21:43:19.5377243Z  * [new tag]             v0.0.31                                  -> v0.0.31
2026-10-26T21:43:19.5377740Z  * [new tag]             v0.0.32                                  -> v0.0.32
2026-10-26T21:43:19.5378237Z  * [new tag]             v0.0.33                                  -> v0.0.33
2026-10-26T21:43:19.5378731Z  * [new tag]             v0.0.34                                  -> v0.0.34
2026-10-26T21:43:19.5379229Z  * [new tag]             v0.0.35                                  -> v0.0.35
2026-10-26T21:43:19.5379729Z  * [new tag]             v0.0.36                                  -> v0.0.36
2026-10-26T21:43:19.5380228Z  * [new tag]             v0.0.37                                  -> v0.0.37
2026-10-26T21:43:19.5380726Z  * [new tag]             v0.0.38                                  -> v0.0.38
2026-10-26T21:43:19.5381233Z  * [new tag]             v0.0.39                                  -> v0.0.39
2026-10-26T21:43:19.5381780Z  * [new tag]             v0.0.4                                   -> v0.0.4
2026-10-26T21:43:19.5382278Z  * [new tag]             v0.0.40                                  -> v0.0.40
2026-10-26T21:43:19.5383099Z  * [new tag]             v0.0.41                                  -> v0.0.41
2026-10-26T21:43:19.5383609Z  * [new tag]             v0.0.42                                  -> v0.0.42
2026-10-26T21:43:19.5384110Z  * [new tag]             v0.0.43                                  -> v0.0.43
2026-10-26T21:43:19.5384608Z  * [new tag]             v0.0.44                                  -> v0.0.44
2026-10-26T21:43:19.5385103Z  * [new tag]             v0.0.45                                  -> v0.0.45
2026-10-26T21:43:19.5385597Z  * [new tag]             v0.0.46                                  -> v0.0.46
2026-10-26T21:43:19.5386268Z  * [new tag]             v0.0.47                                  -> v0.0.47
2026-10-26T21:43:19.5386766Z  * [new tag]             v0.0.48                                  -> v0.0.48
2026-10-26T21:43:19.5387272Z  * [new tag]             v0.0.49                                  -> v0.0.49
2026-10-26T21:43:19.5387779Z  * [new tag]             v0.0.5                                   -> v0.0.5
2026-10-26T21:43:19.5388274Z  * [new tag]             v0.0.50                                  -> v0.0.50
2026-10-26T21:43:19.5388769Z  * [new tag]             v0.0.51                                  -> v0.0.51
2026-10-26T21:43:19.5389262Z  * [new tag]             v0.0.52                                  -> v0.0.52
2026-10-26T21:43:19.5389758Z  * [new tag]             v0.0.53                                  -> v0.0.53
2026-10-26T21:43:19.5390250Z  * [new tag]             v0.0.54                                  -> v0.0.54
2026-10-26T21:43:19.5390744Z  * [new tag]             v0.0.55                                  -> v0.0.55
2026-10-26T21:43:19.5391244Z  * [new tag]             v0.0.56                                  -> v0.0.56
2026-10-26T21:43:19.5391751Z  * [new tag]             v0.0.57                                  -> v0.0.57
2026-10-26T21:43:19.5392257Z  * [new tag]             v0.0.58                                  -> v0.0.58
2026-10-26T21:43:19.5393002Z  * [new tag]             v0.0.59                                  -> v0.0.59
2026-10-26T21:43:19.5393497Z  * [new tag]             v0.0.6                                   -> v0.0.6
2026-10-26T21:43:19.5393986Z  * [new tag]             v0.0.60                                  -> v0.0.60
2026-10-26T21:43:19.5394473Z  * [new tag]             v0.0.61                                  -> v0.0.61
2026-10-26T21:43:19.5394962Z  * [new tag]             v0.0.62                                  -> v0.0.62
2026-10-26T21:43:19.5395454Z  * [new tag]             v0.0.63                                  -> v0.0.63
2026-10-26T21:43:19.5395949Z  * [new tag]             v0.0.64                                  -> v0.0.64
2026-10-26T21:43:19.5396447Z  * [new tag]             v0.0.65                                  -> v0.0.65
2026-10-26T21:43:19.5397083Z  * [new tag]             v0.0.66                                  -> v0.0.66
2026-10-26T21:43:19.5397589Z  * [new tag]             v0.0.67                                  -> v0.0.67
2026-10-26T21:43:19.5398077Z  * [new tag]             v0.0.68                                  -> v0.0.68
2026-10-26T21:43:19.5398563Z  * [new tag]             v0.0.69                                  -> v0.0.69
2026-10-26T21:43:19.5399049Z  * [new tag]             v0.0.7                                   -> v0.0.7
2026-10-26T21:43:19.5399544Z  * [new tag]             v0.0.70                                  -> v0.0.70
2026-10-26T21:43:19.5400038Z  * [new tag]             v0.0.71                                  -> v0.0.71
2026-10-26T21:43:19.5400523Z  * [new tag]             v0.0.72                                  -> v0.0.72
2026-10-26T21:43:19.5401016Z  * [new tag]             v0.0.73                                  -> v0.0.73
2026-10-26T21:43:19.5401504Z  * [new tag]             v0.0.74                                  -> v0.0.74
2026-10-26T21:43:19.5402000Z  * [new tag]             v0.0.75                                  -> v0.0.75
2026-10-26T21:43:19.5402730Z  * [new tag]             v0.0.76                                  -> v0.0.76
2026-10-26T21:43:19.5403234Z  * [new tag]             v0.0.77                                  -> v0.0.77
2026-10-26T21:43:19.5403727Z  * [new tag]             v0.0.78                                  -> v0.0.78
2026-10-26T21:43:19.5404227Z  * [new tag]             v0.0.79                                  -> v0.0.79
2026-10-26T21:43:19.5404717Z  * [new tag]             v0.0.8                                   -> v0.0.8
2026-10-26T21:43:19.5405207Z  * [new tag]             v0.0.9                                   -> v0.0.9
2026-10-26T21:43:19.5405703Z  * [new tag]             v0.10.10                                 -> v0.10.10
2026-10-26T21:43:19.5406568Z  * [new tag]             v0.10.11                                 -> v0.10.11
2026-10-26T21:43:19.5407083Z  * [new tag]             v0.10.12                                 -> v0.10.12
2026-10-26T21:43:19.5407585Z  * [new tag]             v0.10.13                                 -> v0.10.13
2026-10-26T21:43:19.5408089Z  * [new tag]             v0.10.8                                  -> v0.10.8
2026-10-26T21:43:19.5408583Z  * [new tag]             v0.10.9                                  -> v0.10.9
2026-10-26T21:43:19.5409072Z  * [new tag]             v0.11.0                                  -> v0.11.0
2026-10-26T21:43:19.5409561Z  * [new tag]             v0.11.1                                  -> v0.11.1
2026-10-26T21:43:19.5410051Z  * [new tag]             v0.12.0                                  -> v0.12.0
2026-10-26T21:43:19.5410537Z  * [new tag]             v0.12.1                                  -> v0.12.1
2026-10-26T21:43:19.5411405Z  * [new tag]             v0.13.1                                  -> v0.13.1
2026-10-26T21:43:19.5411969Z  * [new tag]             v0.13.2                                  -> v0.13.2
2026-10-26T21:43:19.5412825Z  * [new tag]             v0.13.20                                 -> v0.13.20
2026-10-26T21:43:19.5413365Z  * [new tag]             v0.13.21                                 -> v0.13.21
2026-10-26T21:43:19.5413868Z  * [new tag]             v0.13.22                                 -> v0.13.22
2026-10-26T21:43:19.5414363Z  * [new tag]             v0.13.23                                 -> v0.13.23
2026-10-26T21:43:19.5414864Z  * [new tag]             v0.13.24                                 -> v0.13.24
2026-10-26T21:43:19.5415357Z  * [new tag]             v0.13.25                                 -> v0.13.25
2026-10-26T21:43:19.5415847Z  * [new tag]             v0.13.27                                 -> v0.13.27
2026-10-26T21:43:19.5416341Z  * [new tag]             v0.13.28                                 -> v0.13.28
2026-10-26T21:43:19.5416844Z  * [new tag]             v0.13.3                                  -> v0.13.3
2026-10-26T21:43:19.5417340Z  * [new tag]             v0.13.4                                  -> v0.13.4
2026-10-26T21:43:19.5418015Z  * [new tag]             v0.13.5                                  -> v0.13.5
2026-10-26T21:43:19.5418665Z  * [new tag]             v0.13.6                                  -> v0.13.6
2026-10-26T21:43:19.5419204Z  * [new tag]             v0.13.7                                  -> v0.13.7
2026-10-26T21:43:19.5419694Z  * [new tag]             v0.13.8                                  -> v0.13.8
2026-10-26T21:43:19.5420185Z  * [new tag]             v0.13.9                                  -> v0.13.9
2026-10-26T21:43:19.5420678Z  * [new tag]             v0.14.0                                  -> v0.14.0
2026-10-26T21:43:19.5421560Z  * [new tag]             v0.14.1                                  -> v0.14.1
2026-10-26T21:43:19.5422063Z  * [new tag]             v0.14.2                                  -> v0.14.2
2026-10-26T21:43:19.5422909Z  * [new tag]             v0.15.0                                  -> v0.15.0
2026-10-26T21:43:19.5423422Z  * [new tag]             v0.15.1                                  -> v0.15.1
2026-10-26T21:43:19.5423918Z  * [new tag]             v0.15.2                                  -> v0.15.2
2026-10-26T21:43:19.5424412Z  * [new tag]             v0.15.3                                  -> v0.15.3
2026-10-26T21:43:19.5424908Z  * [new tag]             v0.16.0                                  -> v0.16.0
2026-10-26T21:43:19.5425407Z  * [new tag]             v0.16.1                                  -> v0.16.1
2026-10-26T21:43:19.5425906Z  * [new tag]             v0.16.2                                  -> v0.16.2
2026-10-26T21:43:19.5426400Z  * [new tag]             v0.2.10                                  -> v0.2.10
2026-10-26T21:43:19.5426892Z  * [new tag]             v0.2.11                                  -> v0.2.11
2026-10-26T21:43:19.5427618Z  * [new tag]             v0.2.12                                  -> v0.2.12
2026-10-26T21:43:19.5428110Z  * [new tag]             v0.2.13                                  -> v0.2.13
2026-10-26T21:43:19.5428607Z  * [new tag]             v0.2.14                                  -> v0.2.14
2026-10-26T21:43:19.5429096Z  * [new tag]             v0.2.15                                  -> v0.2.15
2026-10-26T21:43:19.5429587Z  * [new tag]             v0.2.16                                  -> v0.2.16
2026-10-26T21:43:19.5430077Z  * [new tag]             v0.2.17                                  -> v0.2.17
2026-10-26T21:43:19.5430565Z  * [new tag]             v0.2.18                                  -> v0.2.18
2026-10-26T21:43:19.5431065Z  * [new tag]             v0.2.19                                  -> v0.2.19
2026-10-26T21:43:19.5431553Z  * [new tag]             v0.2.2                                   -> v0.2.2
2026-10-26T21:43:19.5432042Z  * [new tag]             v0.2.20                                  -> v0.2.20
2026-10-26T21:43:19.5432973Z  * [new tag]             v0.2.3                                   -> v0.2.3
2026-10-26T21:43:19.5433709Z  * [new tag]             v0.2.4                                   -> v0.2.4
2026-10-26T21:43:19.5434238Z  * [new tag]             v0.2.5                                   -> v0.2.5
2026-10-26T21:43:19.5434722Z  * [new tag]             v0.2.6                                   -> v0.2.6
2026-10-26T21:43:19.5435205Z  * [new tag]             v0.2.7                                   -> v0.2.7
2026-10-26T21:43:19.5435704Z  * [new tag]             v0.2.8                                   -> v0.2.8
2026-10-26T21:43:19.5436194Z  * [new tag]             v0.2.9                                   -> v0.2.9
2026-10-26T21:43:19.5436683Z  * [new tag]             v0.3.0                                   -> v0.3.0
2026-10-26T21:43:19.5437173Z  * [new tag]             v0.3.2                                   -> v0.3.2
2026-10-26T21:43:19.5437668Z  * [new tag]             v0.4.10                                  -> v0.4.10
2026-10-26T21:43:19.5438174Z  * [new tag]             v0.4.11                                  -> v0.4.11
2026-10-26T21:43:19.5438825Z  * [new tag]             v0.4.12                                  -> v0.4.12
2026-10-26T21:43:19.5439336Z  * [new tag]             v0.4.13                                  -> v0.4.13
2026-10-26T21:43:19.5439824Z  * [new tag]             v0.4.3                                   -> v0.4.3
2026-10-26T21:43:19.5440315Z  * [new tag]             v0.4.4                                   -> v0.4.4
2026-10-26T21:43:19.5440808Z  * [new tag]             v0.4.5                                   -> v0.4.5
2026-10-26T21:43:19.5441297Z  * [new tag]             v0.4.6                                   -> v0.4.6
2026-10-26T21:43:19.5441804Z  * [new tag]             v0.4.7                                   -> v0.4.7
2026-10-26T21:43:19.5442294Z  * [new tag]             v0.4.8                                   -> v0.4.8
2026-10-26T21:43:19.5442947Z  * [new tag]             v0.4.9                                   -> v0.4.9
2026-10-26T21:43:19.5443447Z  * [new tag]             v0.5.0                                   -> v0.5.0
2026-10-26T21:43:19.5443934Z  * [new tag]             v0.5.1                                   -> v0.5.1
2026-10-26T21:43:19.5444424Z  * [new tag]             v0.5.2                                   -> v0.5.2
2026-10-26T21:43:19.5444906Z  * [new tag]             v0.5.3                                   -> v0.5.3
2026-10-26T21:43:19.5445386Z  * [new tag]             v0.6.0                                   -> v0.6.0
2026-10-26T21:43:19.5445871Z  * [new tag]             v0.6.2                                   -> v0.6.2
2026-10-26T21:43:19.5446358Z  * [new tag]             v0.6.3                                   -> v0.6.3
2026-10-26T21:43:19.5446844Z  * [new tag]             v0.6.4                                   -> v0.6.4
2026-10-26T21:43:19.5447323Z  * [new tag]             v0.6.5                                   -> v0.6.5
2026-10-26T21:43:19.5447959Z  * [new tag]             v0.6.6                                   -> v0.6.6
2026-10-26T21:43:19.5448441Z  * [new tag]             v0.6.7                                   -> v0.6.7
2026-10-26T21:43:19.5448929Z  * [new tag]             v0.7.0                                   -> v0.7.0
2026-10-26T21:43:19.5449414Z  * [new tag]             v0.7.1                                   -> v0.7.1
2026-10-26T21:43:19.5449893Z  * [new tag]             v0.7.2                                   -> v0.7.2
2026-10-26T21:43:19.5450381Z  * [new tag]             v0.7.3                                   -> v0.7.3
2026-10-26T21:43:19.5450865Z  * [new tag]             v0.8.0                                   -> v0.8.0
2026-10-26T21:43:19.5451348Z  * [new tag]             v0.8.1                                   -> v0.8.1
2026-10-26T21:43:19.5451832Z  * [new tag]             v0.8.2                                   -> v0.8.2
2026-10-26T21:43:19.5452313Z  * [new tag]             v0.9.0                                   -> v0.9.0
2026-10-26T21:43:19.5453016Z  * [new tag]             v0.9.1                                   -> v0.9.1
2026-10-26T21:43:19.5453496Z  * [new tag]             v0.9.2                                   -> v0.9.2
2026-10-26T21:43:19.5453984Z  * [new tag]             v0.9.3                                   -> v0.9.3
2026-10-26T21:43:19.5454473Z  * [new tag]             v0.9.4                                   -> v0.9.4
2026-10-26T21:43:19.5454973Z  * [new tag]             v1.0.0                                   -> v1.0.0
2026-10-26T21:43:19.5455488Z  * [new tag]             v1.0.0a1                                 -> v1.0.0a1
2026-10-26T21:43:19.5455991Z  * [new tag]             v1.0.1                                   -> v1.0.1
2026-10-26T21:43:19.5456479Z  * [new tag]             v1.0.2                                   -> v1.0.2
2026-10-26T21:43:19.5456974Z  * [new tag]             v1.0.3                                   -> v1.0.3
2026-10-26T21:43:19.5457503Z  * [new tag]             v1b-complete                             -> v1b-complete
2026-10-26T21:43:19.5458030Z  * [new tag]             v2.0.0                                   -> v2.0.0
2026-10-26T21:43:19.5458652Z  * [new tag]             v2.0.1                                   -> v2.0.1
2026-10-26T21:43:19.5459154Z  * [new tag]             v2.0.10                                  -> v2.0.10
2026-10-26T21:43:19.5459653Z  * [new tag]             v2.0.11                                  -> v2.0.11
2026-10-26T21:43:19.5460146Z  * [new tag]             v2.0.2                                   -> v2.0.2
2026-10-26T21:43:19.5460634Z  * [new tag]             v2.0.3                                   -> v2.0.3
2026-10-26T21:43:19.5461119Z  * [new tag]             v2.0.4                                   -> v2.0.4
2026-10-26T21:43:19.5461600Z  * [new tag]             v2.0.5                                   -> v2.0.5
2026-10-26T21:43:19.5462089Z  * [new tag]             v2.0.7                                   -> v2.0.7
2026-10-26T21:43:19.5462746Z  * [new tag]             v2.0.8                                   -> v2.0.8
2026-10-26T21:43:19.5463246Z  * [new tag]             v2.0.9                                   -> v2.0.9
2026-10-26T21:43:19.5463731Z  * [new tag]             v2.1.0                                   -> v2.1.0
2026-10-26T21:43:19.5464216Z  * [new tag]             v2.1.1                                   -> v2.1.1
2026-10-26T21:43:19.5464698Z  * [new tag]             v2.1.2                                   -> v2.1.2
2026-10-26T21:43:19.5465181Z  * [new tag]             v2.1.3                                   -> v2.1.3
2026-10-26T21:43:19.5465667Z  * [new tag]             v3.0.0                                   -> v3.0.0
2026-10-26T21:43:19.5466157Z  * [new tag]             v3.0.1                                   -> v3.0.1
2026-10-26T21:43:19.5466643Z  * [new tag]             v3.0.2                                   -> v3.0.2
2026-10-26T21:43:19.5467127Z  * [new tag]             v3.0.3                                   -> v3.0.3
2026-10-26T21:43:19.5467751Z  * [new tag]             v3.1.0                                   -> v3.1.0
2026-10-26T21:43:19.5468247Z  * [new tag]             v3.1.0a2                                 -> v3.1.0a2
2026-10-26T21:43:19.5468759Z  * [new tag]             v3.1.0a3                                 -> v3.1.0a3
2026-10-26T21:43:19.5469258Z  * [new tag]             v3.1.0a4                                 -> v3.1.0a4
2026-10-26T21:43:19.5469755Z  * [new tag]             v3.1.0a5                                 -> v3.1.0a5
2026-10-26T21:43:19.5470255Z  * [new tag]             v3.1.0a6                                 -> v3.1.0a6
2026-10-26T21:43:19.5470752Z  * [new tag]             v3.1.0a7                                 -> v3.1.0a7
2026-10-26T21:43:19.5471258Z  * [new tag]             v3.1.0a8                                 -> v3.1.0a8
2026-10-26T21:43:19.5471749Z  * [new tag]             v3.1.1                                   -> v3.1.1
2026-10-26T21:43:19.5472239Z  * [new tag]             v3.1.10                                  -> v3.1.10
2026-10-26T21:43:19.5472878Z  * [new tag]             v3.1.1a1                                 -> v3.1.1a1
2026-10-26T21:43:19.5473378Z  * [new tag]             v3.1.1a2                                 -> v3.1.1a2
2026-10-26T21:43:19.5473875Z  * [new tag]             v3.1.1a3                                 -> v3.1.1a3
2026-10-26T21:43:19.5474373Z  * [new tag]             v3.1.2                                   -> v3.1.2
2026-10-26T21:43:19.5474864Z  * [new tag]             v3.1.2a1                                 -> v3.1.2a1
2026-10-26T21:43:19.5475362Z  * [new tag]             v3.1.2a2                                 -> v3.1.2a2
2026-10-26T21:43:19.5475861Z  * [new tag]             v3.1.2a3                                 -> v3.1.2a3
2026-10-26T21:43:19.5476350Z  * [new tag]             v3.1.3                                   -> v3.1.3
2026-10-26T21:43:19.5476836Z  * [new tag]             v3.1.4                                   -> v3.1.4
2026-10-26T21:43:19.5477319Z  * [new tag]             v3.1.5                                   -> v3.1.5
2026-10-26T21:43:19.5477811Z  * [new tag]             v3.1.6                                   -> v3.1.6
2026-10-26T21:43:19.5478430Z  * [new tag]             v3.1.7                                   -> v3.1.7
2026-10-26T21:43:19.5478924Z  * [new tag]             v3.1.8                                   -> v3.1.8
2026-10-26T21:43:19.5479407Z  * [new tag]             v3.1.9                                   -> v3.1.9
2026-10-26T21:43:19.5479888Z  * [new tag]             v3.2.0                                   -> v3.2.0
2026-10-26T21:43:19.5480379Z  * [new tag]             v3.2.0a1                                 -> v3.2.0a1
2026-10-26T21:43:19.5480896Z  * [new tag]             v3.2.0a10                                -> v3.2.0a10
2026-10-26T21:43:19.5481404Z  * [new tag]             v3.2.0a2                                 -> v3.2.0a2
2026-10-26T21:43:19.5481961Z  * [new tag]             v3.2.0a3                                 -> v3.2.0a3
2026-10-26T21:43:19.5482642Z  * [new tag]             v3.2.0a4                                 -> v3.2.0a4
2026-10-26T21:43:19.5483154Z  * [new tag]             v3.2.0a5                                 -> v3.2.0a5
2026-10-26T21:43:19.5483661Z  * [new tag]             v3.2.0a6                                 -> v3.2.0a6
2026-10-26T21:43:19.5484169Z  * [new tag]             v3.2.0a7                                 -> v3.2.0a7
2026-10-26T21:43:19.5484670Z  * [new tag]             v3.2.0a8                                 -> v3.2.0a8
2026-10-26T21:43:19.5485169Z  * [new tag]             v3.2.0a9                                 -> v3.2.0a9
2026-10-26T21:43:19.5485678Z  * [new tag]             v3.2.0rc1                                -> v3.2.0rc1
2026-10-26T21:43:19.5486206Z  * [new tag]             v3.2.0rc10                               -> v3.2.0rc10
2026-10-26T21:43:19.5486727Z  * [new tag]             v3.2.0rc11                               -> v3.2.0rc11
2026-10-26T21:43:19.5487240Z  * [new tag]             v3.2.0rc12                               -> v3.2.0rc12
2026-10-26T21:43:19.5487895Z  * [new tag]             v3.2.0rc13                               -> v3.2.0rc13
2026-10-26T21:43:19.5488410Z  * [new tag]             v3.2.0rc14                               -> v3.2.0rc14
2026-10-26T21:43:19.5488914Z  * [new tag]             v3.2.0rc15                               -> v3.2.0rc15
2026-10-26T21:43:19.5489419Z  * [new tag]             v3.2.0rc16                               -> v3.2.0rc16
2026-10-26T21:43:19.5489920Z  * [new tag]             v3.2.0rc17                               -> v3.2.0rc17
2026-10-26T21:43:19.5490431Z  * [new tag]             v3.2.0rc18                               -> v3.2.0rc18
2026-10-26T21:43:19.5490936Z  * [new tag]             v3.2.0rc19                               -> v3.2.0rc19
2026-10-26T21:43:19.5491441Z  * [new tag]             v3.2.0rc2                                -> v3.2.0rc2
2026-10-26T21:43:19.5491952Z  * [new tag]             v3.2.0rc20                               -> v3.2.0rc20
2026-10-26T21:43:19.5492614Z  * [new tag]             v3.2.0rc21                               -> v3.2.0rc21
2026-10-26T21:43:19.5493122Z  * [new tag]             v3.2.0rc22                               -> v3.2.0rc22
2026-10-26T21:43:19.5493630Z  * [new tag]             v3.2.0rc23                               -> v3.2.0rc23
2026-10-26T21:43:19.5494145Z  * [new tag]             v3.2.0rc24                               -> v3.2.0rc24
2026-10-26T21:43:19.5494686Z  * [new tag]             v3.2.0rc25                               -> v3.2.0rc25
2026-10-26T21:43:19.5495194Z  * [new tag]             v3.2.0rc26                               -> v3.2.0rc26
2026-10-26T21:43:19.5495699Z  * [new tag]             v3.2.0rc27                               -> v3.2.0rc27
2026-10-26T21:43:19.5496203Z  * [new tag]             v3.2.0rc28                               -> v3.2.0rc28
2026-10-26T21:43:19.5496706Z  * [new tag]             v3.2.0rc29                               -> v3.2.0rc29
2026-10-26T21:43:19.5497216Z  * [new tag]             v3.2.0rc3                                -> v3.2.0rc3
2026-10-26T21:43:19.5497734Z  * [new tag]             v3.2.0rc30                               -> v3.2.0rc30
2026-10-26T21:43:19.5498375Z  * [new tag]             v3.2.0rc32                               -> v3.2.0rc32
2026-10-26T21:43:19.5498893Z  * [new tag]             v3.2.0rc33                               -> v3.2.0rc33
2026-10-26T21:43:19.5499402Z  * [new tag]             v3.2.0rc34                               -> v3.2.0rc34
2026-10-26T21:43:19.5499915Z  * [new tag]             v3.2.0rc35                               -> v3.2.0rc35
2026-10-26T21:43:19.5500419Z  * [new tag]             v3.2.0rc36                               -> v3.2.0rc36
2026-10-26T21:43:19.5500933Z  * [new tag]             v3.2.0rc37                               -> v3.2.0rc37
2026-10-26T21:43:19.5501444Z  * [new tag]             v3.2.0rc38                               -> v3.2.0rc38
2026-10-26T21:43:19.5501956Z  * [new tag]             v3.2.0rc39                               -> v3.2.0rc39
2026-10-26T21:43:19.5502633Z  * [new tag]             v3.2.0rc4                                -> v3.2.0rc4
2026-10-26T21:43:19.5503157Z  * [new tag]             v3.2.0rc40                               -> v3.2.0rc40
2026-10-26T21:43:19.5503659Z  * [new tag]             v3.2.0rc41                               -> v3.2.0rc41
2026-10-26T21:43:19.5504167Z  * [new tag]             v3.2.0rc42                               -> v3.2.0rc42
2026-10-26T21:43:19.5504673Z  * [new tag]             v3.2.0rc43                               -> v3.2.0rc43
2026-10-26T21:43:19.5505181Z  * [new tag]             v3.2.0rc44                               -> v3.2.0rc44
2026-10-26T21:43:19.5505683Z  * [new tag]             v3.2.0rc45                               -> v3.2.0rc45
2026-10-26T21:43:19.5506202Z  * [new tag]             v3.2.0rc5                                -> v3.2.0rc5
2026-10-26T21:43:19.5506711Z  * [new tag]             v3.2.0rc6                                -> v3.2.0rc6
2026-10-26T21:43:19.5507365Z  * [new tag]             v3.2.0rc7                                -> v3.2.0rc7
2026-10-26T21:43:19.5507876Z  * [new tag]             v3.2.0rc8                                -> v3.2.0rc8
2026-10-26T21:43:19.5508387Z  * [new tag]             v3.2.1                                   -> v3.2.1
2026-10-26T21:43:19.5508879Z  * [new tag]             v3.2.2                                   -> v3.2.2
2026-10-26T21:43:19.5509374Z  * [new tag]             v3.2.3                                   -> v3.2.3
2026-10-26T21:43:19.5509856Z  * [new tag]             v3.2.4                                   -> v3.2.4
2026-10-26T21:43:19.5510340Z  * [new tag]             v3.2.5                                   -> v3.2.5
2026-10-26T21:43:19.5510891Z  * [new ref]             0d5539d16cfeaeef7644bba8775d99e3b44e1695 -> pull/132/merge
2026-10-26T21:43:19.5512771Z ##[endgroup]
2026-10-26T21:43:19.5513248Z ##[group]Determining the checkout info
2026-10-26T21:43:19.5513739Z ##[endgroup]
2026-10-26T21:43:19.5514068Z [command]/usr/bin/git sparse-checkout disable
2026-10-26T21:43:19.5514974Z [command]/usr/bin/git config --local --unset-all extensions.worktreeConfig
2026-10-26T21:43:19.5516077Z ##[group]Checking out the ref
2026-10-26T21:43:19.5516572Z [command]/usr/bin/git checkout --progress --force refs/remotes/pull/132/merge
2026-10-26T21:43:20.5619733Z Updating files:  34% (9819/28132)
2026-10-26T21:43:20.5845153Z Updating files:  35% (9847/28132)
2026-10-26T21:43:20.6058257Z Updating files:  36% (10128/28132)
2026-10-26T21:43:20.6280613Z Updating files:  37% (10409/28132)
2026-10-26T21:43:20.6518317Z Updating files:  38% (10691/28132)
2026-10-26T21:43:20.6743331Z Updating files:  39% (10972/28132)
2026-10-26T21:43:20.6957317Z Updating files:  40% (11253/28132)
2026-10-26T21:43:20.7171605Z Updating files:  41% (11535/28132)
2026-10-26T21:43:20.7387107Z Updating files:  42% (11816/28132)
2026-10-26T21:43:20.7645515Z Updating files:  43% (12097/28132)
2026-10-26T21:43:20.7871270Z Updating files:  44% (12379/28132)
2026-10-26T21:43:20.8085720Z Updating files:  45% (12660/28132)
2026-10-26T21:43:20.8308496Z Updating files:  46% (12941/28132)
2026-10-26T21:43:20.8542010Z Updating files:  47% (13223/28132)
2026-10-26T21:43:20.8825868Z Updating files:  48% (13504/28132)
2026-10-26T21:43:20.9033057Z Updating files:  49% (13785/28132)
2026-10-26T21:43:20.9263074Z Updating files:  50% (14066/28132)
2026-10-26T21:43:20.9466429Z Updating files:  51% (14348/28132)
2026-10-26T21:43:20.9665694Z Updating files:  52% (14629/28132)
2026-10-26T21:43:20.9904466Z Updating files:  53% (14910/28132)
2026-10-26T21:43:21.0119727Z Updating files:  54% (15192/28132)
2026-10-26T21:43:21.0332309Z Updating files:  55% (15473/28132)
2026-10-26T21:43:21.0548301Z Updating files:  56% (15754/28132)
2026-10-26T21:43:21.0800810Z Updating files:  57% (16036/28132)
2026-10-26T21:43:21.1013455Z Updating files:  58% (16317/28132)
2026-10-26T21:43:21.1230637Z Updating files:  59% (16598/28132)
2026-10-26T21:43:21.1520810Z Updating files:  60% (16880/28132)
2026-10-26T21:43:21.1741137Z Updating files:  61% (17161/28132)
2026-10-26T21:43:21.1965154Z Updating files:  62% (17442/28132)
2026-10-26T21:43:21.2186327Z Updating files:  63% (17724/28132)
2026-10-26T21:43:21.2381408Z Updating files:  64% (18005/28132)
2026-10-26T21:43:21.2614820Z Updating files:  65% (18286/28132)
2026-10-26T21:43:21.2809634Z Updating files:  66% (18568/28132)
2026-10-26T21:43:21.3033494Z Updating files:  67% (18849/28132)
2026-10-26T21:43:21.3247544Z Updating files:  68% (19130/28132)
2026-10-26T21:43:21.3446090Z Updating files:  69% (19412/28132)
2026-10-26T21:43:21.3668313Z Updating files:  70% (19693/28132)
2026-10-26T21:43:21.3909085Z Updating files:  71% (19974/28132)
2026-10-26T21:43:21.4150803Z Updating files:  72% (20256/28132)
2026-10-26T21:43:21.4383499Z Updating files:  73% (20537/28132)
2026-10-26T21:43:21.4601064Z Updating files:  74% (20818/28132)
2026-10-26T21:43:21.4799040Z Updating files:  75% (21099/28132)
2026-10-26T21:43:21.4984687Z Updating files:  76% (21381/28132)
2026-10-26T21:43:21.5276728Z Updating files:  77% (21662/28132)
2026-10-26T21:43:21.5524057Z Updating files:  78% (21943/28132)
2026-10-26T21:43:21.5584518Z Updating files:  79% (22225/28132)
2026-10-26T21:43:21.5784957Z Updating files:  79% (22314/28132)
2026-10-26T21:43:21.6229325Z Updating files:  80% (22506/28132)
2026-10-26T21:43:21.6526896Z Updating files:  81% (22787/28132)
2026-10-26T21:43:21.6823121Z Updating files:  82% (23069/28132)
2026-10-26T21:43:21.7048942Z Updating files:  83% (23350/28132)
2026-10-26T21:43:21.7345575Z Updating files:  84% (23631/28132)
2026-10-26T21:43:21.7650460Z Updating files:  85% (23913/28132)
2026-10-26T21:43:21.7890888Z Updating files:  86% (24194/28132)
2026-10-26T21:43:21.8076966Z Updating files:  87% (24475/28132)
2026-10-26T21:43:21.8363421Z Updating files:  88% (24757/28132)
2026-10-26T21:43:21.8594955Z Updating files:  89% (25038/28132)
2026-10-26T21:43:21.8808464Z Updating files:  90% (25319/28132)
2026-10-26T21:43:21.9066862Z Updating files:  91% (25601/28132)
2026-10-26T21:43:21.9319703Z Updating files:  92% (25882/28132)
2026-10-26T21:43:21.9563003Z Updating files:  93% (26163/28132)
2026-10-26T21:43:21.9840249Z Updating files:  94% (26445/28132)
2026-10-26T21:43:22.0091017Z Updating files:  95% (26726/28132)
2026-10-26T21:43:22.0318006Z Updating files:  96% (27007/28132)
2026-10-26T21:43:22.0565314Z Updating files:  97% (27289/28132)
2026-10-26T21:43:22.0801216Z Updating files:  98% (27570/28132)
2026-10-26T21:43:22.1099831Z Updating files:  99% (27851/28132)
2026-10-26T21:43:22.1100484Z Updating files: 100% (28132/28132)
2026-10-26T21:43:22.1103220Z Updating files: 100% (28132/28132), done.
2026-10-26T21:43:22.1488974Z Note: switching to 'refs/remotes/pull/132/merge'.
2026-10-26T21:43:22.1489765Z 
2026-10-26T21:43:22.1490487Z You are in 'detached HEAD' state. You can look around, make experimental
2026-10-26T21:43:22.1491711Z changes and commit them, and you can discard any commits you make in this
2026-10-26T21:43:22.1492697Z state without impacting any branches by switching back to a branch.
2026-10-26T21:43:22.1493180Z 
2026-10-26T21:43:22.1493482Z If you want to create a new branch to retain commits you create, you may
2026-10-26T21:43:22.1494431Z do so (now or later) by using -c with the switch command. Example:
2026-10-26T21:43:22.1494845Z 
2026-10-26T21:43:22.1495008Z   git switch -c <new-branch-name>
2026-10-26T21:43:22.1495281Z 
2026-10-26T21:43:22.1495430Z Or undo this operation with:
2026-10-26T21:43:22.1495682Z 
2026-10-26T21:43:22.1495810Z   git switch -
2026-10-26T21:43:22.1496002Z 
2026-10-26T21:43:22.1496341Z Turn off this advice by setting config variable advice.detachedHead to false
2026-10-26T21:43:22.1496840Z 
2026-10-26T21:43:22.1497410Z HEAD is now at 0d5539d16 Merge 628f943a058dd6553db998c13d36ebca0709895f into a55e8207108a6658d86ef864ebe58c3180c29476
2026-10-26T21:43:22.1554371Z ##[endgroup]
2026-10-26T21:43:22.1599406Z [command]/usr/bin/git log -1 --format=%H
2026-10-26T21:43:22.1629410Z 0d5539d16cfeaeef7644bba8775d99e3b44e1695
2026-10-26T21:43:22.1848733Z ##[group]Run python3 -m scripts.ci.memory_sampler start --out "$RUNNER_TEMP/memory-sampler.json"
2026-10-26T21:43:22.1849523Z [36;1mpython3 -m scripts.ci.memory_sampler start --out "$RUNNER_TEMP/memory-sampler.json"[0m
2026-10-26T21:43:22.2140997Z shell: /usr/bin/bash -e {0}
2026-10-26T21:43:22.2141408Z ##[endgroup]
2026-10-26T21:43:22.2768352Z memory_sampler started pid=2309 out=/home/runner/work/_temp/memory-sampler.json
2026-10-26T21:43:22.2974471Z ##[group]Run astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d
2026-10-26T21:43:22.2974888Z with:
2026-10-26T21:43:22.2975098Z   python-version: 3.12
2026-10-26T21:43:22.2975348Z   activate-environment: false
2026-10-26T21:43:22.2975602Z   no-project: false
2026-10-26T21:43:22.2975899Z   working-directory: /home/runner/work/spec-kitty/spec-kitty
2026-10-26T21:43:22.2978398Z   github-token: ***
2026-10-26T21:43:22.2978629Z   enable-cache: auto
2026-10-26T21:43:22.2979208Z   cache-dependency-glob: **/*requirements*.txt
**/*requirements*.in
**/*constraints*.txt
**/*constraints*.in
**/pyproject.toml
**/uv.lock
**/*.py.lock

2026-10-26T21:43:22.2980025Z   restore-cache: true
2026-10-26T21:43:22.2980245Z   save-cache: true
2026-10-26T21:43:22.2980459Z   prune-cache: false
2026-10-26T21:43:22.2980677Z   cache-python: false
2026-10-26T21:43:22.2980910Z   ignore-nothing-to-cache: false
2026-10-26T21:43:22.2981184Z   ignore-empty-workdir: false
2026-10-26T21:43:22.2981480Z   download-from-astral-mirror: true
2026-10-26T21:43:22.2981766Z   add-problem-matchers: true
2026-10-26T21:43:22.2982006Z   quiet: false
2026-10-26T21:43:22.2982218Z   resolution-strategy: highest
2026-10-26T21:43:22.2982669Z ##[endgroup]
2026-10-26T21:43:22.4912332Z Trying to find version for uv in: /home/runner/work/spec-kitty/spec-kitty/uv.toml
2026-10-26T21:43:22.4913956Z Could not find file: /home/runner/work/spec-kitty/spec-kitty/uv.toml
2026-10-26T21:43:22.4915254Z Trying to find version for uv in: /home/runner/work/spec-kitty/spec-kitty/pyproject.toml
2026-10-26T21:43:22.4961776Z Could not determine uv version from uv.toml or pyproject.toml. Falling back to latest.
2026-10-26T21:43:22.4967696Z Fetching manifest data from https://raw.githubusercontent.com/astral-sh/versions/main/v1/uv.ndjson ...
2026-10-26T21:43:22.5945659Z Downloading uv from "https://releases.astral.sh/github/uv/releases/download/0.13.5/uv-x86_64-unknown-linux-gnu.tar.gz" ...
2026-10-26T21:43:22.9401034Z [command]/usr/bin/tar xz --warning=no-unknown-keyword --overwrite -C /home/runner/work/_temp/8a09bab4-58f3-471e-b374-7b39299be437 -f /home/runner/work/_temp/8dcd729d-1d18-4124-a694-eed71341a561
2026-10-26T21:43:23.2637750Z Added /home/runner/.local/bin to the path
2026-10-26T21:43:23.2638306Z Added /opt/hostedtoolcache/uv/0.13.5/x86_64 to the path
2026-10-26T21:43:23.2638746Z Set UV_PYTHON_INSTALL_DIR to /home/runner/work/_temp/uv-python-dir
2026-10-26T21:43:23.2639181Z Added /home/runner/work/_temp/uv-python-dir to the path
2026-10-26T21:43:23.2639505Z Set UV_PYTHON to 3.12
2026-10-26T21:43:23.2659465Z Set UV_CACHE_DIR to /home/runner/work/_temp/setup-uv-cache
2026-10-26T21:43:23.2659911Z Successfully installed uv version 0.13.5
2026-10-26T21:43:23.2661846Z Searching files using cache dependency glob: /home/runner/work/spec-kitty/spec-kitty/**/*requirements*.txt,/home/runner/work/spec-kitty/spec-kitty/**/*requirements*.in,/home/runner/work/spec-kitty/spec-kitty/**/*constraints*.txt,/home/runner/work/spec-kitty/spec-kitty/**/*constraints*.in,/home/runner/work/spec-kitty/spec-kitty/**/pyproject.toml,/home/runner/work/spec-kitty/spec-kitty/**/uv.lock,/home/runner/work/spec-kitty/spec-kitty/**/*.py.lock
2026-10-26T21:43:26.0511856Z /home/runner/work/spec-kitty/spec-kitty/pyproject.toml
2026-10-26T21:43:26.1369755Z /home/runner/work/spec-kitty/spec-kitty/src/kernel/pyproject.toml
2026-10-26T21:43:26.7574623Z /home/runner/work/spec-kitty/spec-kitty/uv.lock
2026-10-26T21:43:26.7594871Z Found 3 files to hash.
2026-10-26T21:43:26.7676448Z Trying to restore cache from GitHub Actions cache with key: setup-uv-2-x86_64-unknown-linux-gnu-ubuntu-24.04-3.12-1c37a6299c72891dd45e13b227c87d319343a0af98363daa6a402e69b1188d5f
2026-10-26T21:43:26.9733923Z Cache hit for: setup-uv-2-x86_64-unknown-linux-gnu-ubuntu-24.04-3.12-1c37a6299c72891dd45e13b227c87d319343a0af98363daa6a402e69b1188d5f
2026-10-26T21:43:27.3948327Z Received 1054 of 1054 (100.0%), 0.0 MBs/sec
2026-10-26T21:43:27.3949453Z Cache Size: ~0 MB (1054 B)
2026-10-26T21:43:27.3977174Z [command]/usr/bin/tar -xf /home/runner/work/_temp/559156fb-ff91-439b-9960-e3ebf5df077f/cache.tzst -P -C /home/runner/work/spec-kitty/spec-kitty --use-compress-program unzstd
2026-10-26T21:43:27.4059583Z Cache restored successfully
2026-10-26T21:43:27.4064485Z cache restored from GitHub Actions cache with key: setup-uv-2-x86_64-unknown-linux-gnu-ubuntu-24.04-3.12-1c37a6299c72891dd45e13b227c87d319343a0af98363daa6a402e69b1188d5f
2026-10-26T21:43:27.5251038Z ##[group]Run uv sync --frozen --all-extras
2026-10-26T21:43:27.5251478Z [36;1muv sync --frozen --all-extras[0m
2026-10-26T21:43:27.5251881Z [36;1muv run --frozen python -m pytest tests/architectural \[0m
2026-10-26T21:43:27.5252878Z [36;1m  -m "not performance and not stress and not timing" \[0m
2026-10-26T21:43:27.5253267Z [36;1m  -n 4 --dist loadfile \[0m
2026-10-26T21:43:27.5253665Z [36;1m  --deselect tests/architectural/test_no_legacy_terminology.py \[0m
2026-10-26T21:43:27.5254151Z [36;1m  --deselect tests/architectural/test_layer_rules.py \[0m
2026-10-26T21:43:27.5254603Z [36;1m  --deselect tests/architectural/test_pyproject_shape.py \[0m
2026-10-26T21:43:27.5255118Z [36;1m  --deselect tests/architectural/test_archive_root_byte_identical.py \[0m
2026-10-26T21:43:27.5255654Z [36;1m  -p scripts.ci.battery_partition_plugin --battery-part fast \[0m
2026-10-26T21:43:27.5256133Z [36;1m  --junitxml=out/reports/xunit-architectural-fast.xml[0m
2026-10-26T21:43:27.5322032Z shell: /usr/bin/bash -e {0}
2026-10-26T21:43:27.5322327Z env:
2026-10-26T21:43:27.5322824Z   UV_PYTHON_INSTALL_DIR: /home/runner/work/_temp/uv-python-dir
2026-10-26T21:43:27.5323233Z   UV_PYTHON: 3.12
2026-10-26T21:43:27.5323532Z   UV_CACHE_DIR: /home/runner/work/_temp/setup-uv-cache
2026-10-26T21:43:27.5323882Z ##[endgroup]
2026-10-26T21:43:27.5524936Z Using CPython 3.12.3 interpreter at: /usr/bin/python3.12
2026-10-26T21:43:27.5525487Z Creating virtual environment at: .venv
2026-10-26T21:43:27.5794550Z    Building spec-kitty-cli @ file:///home/runner/work/spec-kitty/spec-kitty
2026-10-26T21:43:27.7173249Z Downloading cryptography (4.5MiB)
2026-10-26T21:43:27.7175055Z Downloading pygments (1.2MiB)
2026-10-26T21:43:27.7176823Z Downloading networkx (2.0MiB)
2026-10-26T21:43:27.7181436Z Downloading mypy (14.1MiB)
2026-10-26T21:43:27.7184512Z Downloading lxml (5.0MiB)
2026-10-26T21:43:27.7193128Z Downloading pip (1.7MiB)
2026-10-26T21:43:27.7200963Z Downloading ruff (10.8MiB)
2026-10-26T21:43:27.7219452Z Downloading pydantic-core (2.0MiB)
2026-10-26T21:43:27.7225577Z Downloading libcst (2.2MiB)
2026-10-26T21:43:28.0490326Z  Downloaded pygments
2026-10-26T21:43:28.0815146Z  Downloaded pip
2026-10-26T21:43:28.0816611Z  Downloaded networkx
2026-10-26T21:43:28.0878944Z  Downloaded pydantic-core
2026-10-26T21:43:28.0954296Z  Downloaded libcst
2026-10-26T21:43:28.1367525Z  Downloaded cryptography
2026-10-26T21:43:28.1483505Z  Downloaded lxml
2026-10-26T21:43:28.2195153Z  Downloaded ruff
2026-10-26T21:43:28.3053410Z  Downloaded mypy
2026-10-26T21:43:29.5077464Z       Built spec-kitty-cli @ file:///home/runner/work/spec-kitty/spec-kitty
2026-10-26T21:43:29.5386635Z Prepared 126 packages in 1.98s
2026-10-26T21:43:29.6177655Z Installed 126 packages in 78ms
2026-10-26T21:43:29.6178631Z  + annotated-doc==0.0.4
2026-10-26T21:43:29.6179217Z  + annotated-types==0.7.0
2026-10-26T21:43:29.6179828Z  + anyio==4.15.1
2026-10-26T21:43:29.6180360Z  + arrow==1.4.0
2026-10-26T21:43:29.6180871Z  + attrs==26.1.0
2026-10-26T21:43:29.6181413Z  + bandit==1.9.4
2026-10-26T21:43:29.6182008Z  + boolean-py==5.0
2026-10-26T21:43:29.6182739Z  + build==1.4.4
2026-10-26T21:43:29.6183275Z  + cachecontrol==0.14.4
2026-10-26T21:43:29.6183872Z  + certifi==2026.4.22
2026-10-26T21:43:29.6184413Z  + cffi==2.0.0
2026-10-26T21:43:29.6184935Z  + chardet==5.2.0
2026-10-26T21:43:29.6185494Z  + charset-normalizer==3.4.7
2026-10-26T21:43:29.6186112Z  + click==8.3.3
2026-10-26T21:43:29.6186630Z  + codespell==2.4.3
2026-10-26T21:43:29.6187176Z  + coverage==7.13.5
2026-10-26T21:43:29.6187722Z  + cryptography==50.0.0
2026-10-26T21:43:29.6188320Z  + cyclonedx-bom==7.3.0
2026-10-26T21:43:29.6188930Z  + cyclonedx-python-lib==11.7.0
2026-10-26T21:43:29.6189589Z  + defusedxml==0.7.1
2026-10-26T21:43:29.6190148Z  + diff-cover==10.2.0
2026-10-26T21:43:29.6190699Z  + execnet==2.1.2
2026-10-26T21:43:29.6191066Z  + filelock==3.29.0
2026-10-26T21:43:29.6191413Z  + fqdn==1.5.1
2026-10-26T21:43:29.6191752Z  + google-re2==1.1.20251105
2026-10-26T21:43:29.6192134Z  + h11==0.16.0
2026-10-26T21:43:29.6192955Z  + hatchling==1.31.0
2026-10-26T21:43:29.6193355Z  + httpcore==1.0.9
2026-10-26T21:43:29.6193718Z  + httpx==0.28.1
2026-10-26T21:43:29.6194063Z  + httpx-sse==0.4.3
2026-10-26T21:43:29.6194619Z  + idna==3.15
2026-10-26T21:43:29.6194947Z  + iniconfig==2.3.0
2026-10-26T21:43:29.6195305Z  + isoduration==20.11.0
2026-10-26T21:43:29.6195671Z  + jinja2==3.1.6
2026-10-26T21:43:29.6196017Z  + jsonpointer==3.1.1
2026-10-26T21:43:29.6196381Z  + jsonschema==4.26.0
2026-10-26T21:43:29.6196789Z  + jsonschema-specifications==2025.9.1
2026-10-26T21:43:29.6197248Z  + lark==1.3.1
2026-10-26T21:43:29.6197576Z  + libcst==1.8.6
2026-10-26T21:43:29.6197908Z  + librt==0.9.0
2026-10-26T21:43:29.6198278Z  + license-expression==30.4.4
2026-10-26T21:43:29.6198697Z  + linkify-it-py==2.1.0
2026-10-26T21:43:29.6199068Z  + lxml==6.1.0
2026-10-26T21:43:29.6199412Z  + markdown-it-py==4.0.0
2026-10-26T21:43:29.6199812Z  + markupsafe==3.0.3
2026-10-26T21:43:29.6200163Z  + mcp==1.29.0
2026-10-26T21:43:29.6200525Z  + mdit-py-plugins==0.5.0
2026-10-26T21:43:29.6200913Z  + mdurl==0.1.2
2026-10-26T21:43:29.6201252Z  + msgpack==1.2.1
2026-10-26T21:43:29.6201644Z  + mutmut==3.5.0
2026-10-26T21:43:29.6202179Z  + mypy==1.20.2
2026-10-26T21:43:29.6202748Z  + mypy-extensions==1.1.0
2026-10-26T21:43:29.6209478Z  + networkx==3.6.1
2026-10-26T21:43:29.6209909Z  + packageurl-python==0.17.6
2026-10-26T21:43:29.6210334Z  + packaging==26.2
2026-10-26T21:43:29.6210690Z  + pathspec==1.1.0
2026-10-26T21:43:29.6211026Z  + pip==26.2.1
2026-10-26T21:43:29.6211366Z  + pip-api==0.0.34
2026-10-26T21:43:29.6211725Z  + pip-audit==2.10.0
2026-10-26T21:43:29.6212123Z  + pip-requirements-parser==32.0.1
2026-10-26T21:43:29.6212795Z  + platformdirs==4.9.6
2026-10-26T21:43:29.6213171Z  + pluggy==1.6.0
2026-10-26T21:43:29.6213518Z  + psutil==7.2.2
2026-10-26T21:43:29.6213969Z  + py-cpuinfo2==10.1.1
2026-10-26T21:43:29.6214399Z  + py-serializable==2.1.0
2026-10-26T21:43:29.6214808Z  + pycparser==3.0
2026-10-26T21:43:29.6215264Z  + pydantic==2.13.3
2026-10-26T21:43:29.6215776Z  + pydantic-core==2.46.3
2026-10-26T21:43:29.6216218Z  + pydantic-settings==2.15.0
2026-10-26T21:43:29.6216651Z  + pygments==2.20.0
2026-10-26T21:43:29.6217126Z  + pyjwt==2.15.1
2026-10-26T21:43:29.6217574Z  + pyparsing==3.3.2
2026-10-26T21:43:29.6218073Z  + pyproject-hooks==1.2.0
2026-10-26T21:43:29.6218484Z  + pytest==9.0.3
2026-10-26T21:43:29.6218950Z  + pytest-asyncio==1.3.0
2026-10-26T21:43:29.6219365Z  + pytest-benchmark==5.3.0
2026-10-26T21:43:29.6219818Z  + pytest-cov==7.1.0
2026-10-26T21:43:29.6220275Z  + pytest-timeout==2.4.0
2026-10-26T21:43:29.6220729Z  + pytest-xdist==3.8.0
2026-10-26T21:43:29.6221184Z  + pytestarch==4.0.1
2026-10-26T21:43:29.6221749Z  + python-dateutil==2.9.0.post0
2026-10-26T21:43:29.6222184Z  + python-dotenv==1.2.3
2026-10-26T21:43:29.6222870Z  + python-multipart==0.0.32
2026-10-26T21:43:29.6223285Z  + python-ulid==3.1.0
2026-10-26T21:43:29.6223650Z  + pyyaml==6.0.3
2026-10-26T21:43:29.6224154Z  + readchar==4.2.2
2026-10-26T21:43:29.6224621Z  + referencing==0.37.0
2026-10-26T21:43:29.6225038Z  + requests==2.33.1
2026-10-26T21:43:29.6225473Z  + respx==0.23.1
2026-10-26T21:43:29.6225937Z  + rfc3339-validator==0.1.4
2026-10-26T21:43:29.6226363Z  + rfc3986-validator==0.1.1
2026-10-26T21:43:29.6226827Z  + rfc3987-syntax==1.1.0
2026-10-26T21:43:29.6227207Z  + rich==15.0.0
2026-10-26T21:43:29.6227688Z  + rpds-py==0.30.0
2026-10-26T21:43:29.6228147Z  + ruamel-yaml==0.19.1
2026-10-26T21:43:29.6228576Z  + ruff==0.15.12
2026-10-26T21:43:29.6229052Z  + setproctitle==1.3.7
2026-10-26T21:43:29.6229503Z  + shellingham==1.5.4
2026-10-26T21:43:29.6229943Z  + six==1.17.0
2026-10-26T21:43:29.6230406Z  + socksio==1.0.0
2026-10-26T21:43:29.6230809Z  + sortedcontainers==2.4.0
2026-10-26T21:43:29.6231861Z  + spec-kitty-cli==4.0.0rc6 (from file:///home/runner/work/spec-kitty/spec-kitty)
2026-10-26T21:43:29.6232756Z  + spec-kitty-events==10.4.0
2026-10-26T21:43:29.6233190Z  + spec-kitty-tracker==0.5.2
2026-10-26T21:43:29.6233604Z  + sse-starlette==3.4.8
2026-10-26T21:43:29.6234234Z  + starlette==1.6.0
2026-10-26T21:43:29.6234605Z  + stevedore==5.7.0
2026-10-26T21:43:29.6234962Z  + textual==8.2.4
2026-10-26T21:43:29.6235307Z  + toml==0.10.2
2026-10-26T21:43:29.6235822Z  + tomli==2.4.1
2026-10-26T21:43:29.6236158Z  + tomli-w==1.2.0
2026-10-26T21:43:29.6236532Z  + trove-classifiers==2026.6.1.19
2026-10-26T21:43:29.6236961Z  + typer==0.24.2
2026-10-26T21:43:29.6237336Z  + types-jsonschema==4.26.0.20260408
2026-10-26T21:43:29.6237793Z  + types-psutil==7.2.2.20260408
2026-10-26T21:43:29.6238228Z  + types-pyyaml==6.0.12.20260408
2026-10-26T21:43:29.6238686Z  + types-requests==2.33.0.20260408
2026-10-26T21:43:29.6239143Z  + types-toml==0.10.8.20260408
2026-10-26T21:43:29.6239641Z  + typing-extensions==4.16.0
2026-10-26T21:43:29.6240084Z  + typing-inspection==0.4.2
2026-10-26T21:43:29.6240490Z  + tzdata==2026.2
2026-10-26T21:43:29.6240840Z  + uc-micro-py==2.0.0
2026-10-26T21:43:29.6241276Z  + uri-template==1.3.0
2026-10-26T21:43:29.6241648Z  + urllib3==2.8.0
2026-10-26T21:43:29.6242093Z  + uvicorn==0.52.4
2026-10-26T21:43:29.6242630Z  + webcolors==25.10.0
2026-10-26T21:45:28.2563444Z ##[warning]battery architectural: 20 files without a timing get the median 2.04s; 1 stale timing keys; 20 missing: tests/architectural/test_catalog_mission_single_reader.py, tests/architectural/test_charter_kind_vocabulary_single_authority.py, tests/architectural/test_commit_recipe_strings.py, tests/architectural/test_commit_scope_owner.py, tests/architectural/test_evidence_gates_check_origin.py, tests/architectural/test_git_path_listing_owner.py, tests/architectural/test_kind_table_derivation.py, tests/architectural/test_mission_state_repair_sole_caller.py, tests/architectural/test_mission_write_discipline.py, tests/architectural/test_no_config_key_spelled_as_module_path.py, ...; 1 stale: tests/architectural/test_no_process_name_wide_dashboard_kill.py
2026-10-26T21:45:28.2591532Z ============================= test session starts ==============================
2026-10-26T21:45:28.2623464Z platform linux -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0
2026-10-26T21:45:28.2654045Z benchmark: 5.3.0 (defaults: timer=time.perf_counter disable_gc=False min_rounds=5 min_time=0.000005 max_time=1.0 calibration_precision=10 warmup=False warmup_iterations=100000)
2026-10-26T21:45:28.2683275Z rootdir: /home/runner/work/spec-kitty/spec-kitty
2026-10-26T21:45:28.2713198Z configfile: pytest.ini
2026-10-26T21:45:28.2743445Z plugins: asyncio-1.3.0, benchmark-5.3.0, timeout-2.4.0, respx-0.23.1, cov-7.1.0, xdist-3.8.0, anyio-4.15.1
2026-10-26T21:45:28.2773650Z asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
2026-10-26T21:45:28.2803269Z timeout: 240.0s
2026-10-26T21:45:28.2843235Z timeout method: signal
2026-10-26T21:45:28.2863307Z timeout func_only: False
2026-10-26T21:45:28.2943872Z created: 4/4 workers
2026-10-26T21:45:28.2973709Z 4 workers [800 items]
2026-10-26T21:45:28.3002865Z 
2026-10-26T21:45:29.5118735Z ........................................................................ [  9%]
2026-10-26T21:45:35.8633913Z ...................................................s.................... [ 18%]
2026-10-26T21:45:37.0393524Z ........................................................................ [ 27%]
2026-10-26T21:45:38.1235540Z ........................................................................ [ 36%]
2026-10-26T21:45:39.7870365Z ........................................................................ [ 45%]
2026-10-26T21:45:40.6463809Z ........................................................................ [ 54%]
2026-10-26T21:45:43.9821955Z ........................................................................ [ 63%]
2026-10-26T21:45:59.8950755Z ........................................................................ [ 72%]
2026-10-26T21:46:03.6523572Z ........................................................................ [ 81%]
2026-10-26T21:46:39.2823458Z ...........................................................F............ [ 90%]
2026-10-26T21:47:12.5875119Z ........................................................................ [ 99%]
2026-10-26T21:47:35.1013540Z ........                                                                 [100%]
2026-10-26T21:47:35.1014760Z =================================== FAILURES ===================================
2026-10-26T21:47:35.1015698Z _______________ test_ast_scan_no_direct_status_imports_repo_wide _______________
2026-10-26T21:47:35.1016810Z [gw3] linux -- Python 3.12.3 /home/runner/work/spec-kitty/spec-kitty/.venv/bin/python
2026-10-26T21:47:35.1018247Z tests/architectural/test_status_module_boundary.py:418: in test_ast_scan_no_direct_status_imports_repo_wide
2026-10-26T21:47:35.1019519Z     assert not violations, (
2026-10-26T21:47:35.1020564Z E   AssertionError: Direct status submodule imports found outside the allow-list (1 violations):
2026-10-26T21:47:35.1022286Z E       /home/runner/work/spec-kitty/spec-kitty/src/runtime/next/discovery.py:288: specify_cli.status.review_roles
2026-10-26T21:47:35.1023477Z E     
2026-10-26T21:47:35.1023966Z E     All imports from status/ must go through `from specify_cli.status import X`.
2026-10-26T21:47:35.1025005Z E     To add a temporary exemption: add the file path to _WP10_DEFERRED_FILES with a comment explaining WHY and which WP will fix it.
2026-10-26T21:47:35.1026241Z E     Permanent exemptions (C-004 plumbing): coordination/status_transition.py, coordination/transaction.py.
2026-10-26T21:47:35.1027424Z E   assert not ['/home/runner/work/spec-kitty/spec-kitty/src/runtime/next/discovery.py:288: specify_cli.status.review_roles']
2026-10-26T21:47:35.1028606Z - generated xml file: /home/runner/work/spec-kitty/spec-kitty/out/reports/xunit-architectural-fast.xml -
2026-10-26T21:47:35.1029381Z battery part fast: 34 files
2026-10-26T21:47:35.1029766Z workers seen: gw0, gw1, gw2, gw3
2026-10-26T21:47:35.1030517Z slowest test: tests/architectural/test_json_contract_enumeration.py::test_real_zero_wp_status (27.2s)
2026-10-26T21:47:35.1031357Z   tests/architectural/test_inline_meta_read_gate.py: 106.0s
2026-10-26T21:47:35.1031843Z   tests/architectural/test_untrusted_path_containment.py: 43.1s
2026-10-26T21:47:35.1032333Z   tests/architectural/test_no_duplicate_suite_execution.py: 37.8s
2026-10-26T21:47:35.1033195Z   tests/architectural/test_owned_checkout_single_authority.py: 36.4s
2026-10-26T21:47:35.1033695Z   tests/architectural/test_no_write_side_rederivation.py: 32.1s
2026-10-26T21:47:35.1034154Z   tests/architectural/test_safe_commit_import_boundary.py: 29.3s
2026-10-26T21:47:35.1034626Z   tests/architectural/test_json_contract_enumeration.py: 29.3s
2026-10-26T21:47:35.1035068Z   tests/architectural/test_docs_cli_reference_parity.py: 25.3s
2026-10-26T21:47:35.1035501Z   tests/architectural/test_src_reachability_guard.py: 22.9s
2026-10-26T21:47:35.1035904Z   tests/architectural/test_no_dead_modules.py: 21.7s
2026-10-26T21:47:35.1037785Z ##[warning]tests/architectural/test_coord_read_residuals_closeout.py: 13.5s exceeds its 13s roster budget
2026-10-26T21:47:35.1039964Z ##[warning]tests/architectural/test_docs_cli_reference_parity.py: 25.3s exceeds its 10s roster budget
2026-10-26T21:47:35.1042145Z ##[warning]tests/architectural/test_inline_meta_read_gate.py: 106.0s exceeds its 88s roster budget
2026-10-26T21:47:35.1044380Z ##[warning]tests/architectural/test_no_dead_modules.py: 21.7s exceeds its 14s roster budget
2026-10-26T21:47:35.1046077Z ##[warning]tests/architectural/test_no_duplicate_suite_execution.py: 37.8s exceeds its 13s roster budget
2026-10-26T21:47:35.1047834Z ##[warning]tests/architectural/test_no_write_side_rederivation.py: 32.1s exceeds its 13s roster budget
2026-10-26T21:47:35.1050886Z ##[warning]tests/architectural/test_owned_checkout_single_authority.py: 36.4s exceeds its 24s roster budget
2026-10-26T21:47:35.1053455Z ##[warning]tests/architectural/test_safe_commit_import_boundary.py: 29.3s exceeds its 24s roster budget
2026-10-26T21:47:35.1055225Z ##[warning]tests/architectural/test_src_reachability_guard.py: 22.9s exceeds its 15s roster budget
2026-10-26T21:47:35.1057114Z ##[warning]tests/architectural/test_status_module_boundary.py: 13.1s exceeds its 10s roster budget
2026-10-26T21:47:35.1058829Z ##[warning]tests/architectural/test_timing_coverage_invariant.py: 21.1s exceeds its 13s roster budget
2026-10-26T21:47:35.1060803Z ##[warning]tests/architectural/test_untrusted_path_containment.py: 43.1s exceeds its 33s roster budget
2026-10-26T21:47:35.1061802Z ============================== slowest durations ===============================
2026-10-26T21:47:35.1062639Z 27.14s setup    tests/architectural/test_json_contract_enumeration.py::test_real_zero_wp_status
2026-10-26T21:47:35.1063424Z 24.08s call     tests/architectural/test_docs_cli_reference_parity.py::test_retired_check_residual_option_is_absent
2026-10-26T21:47:35.1064165Z 22.55s setup    tests/architectural/test_src_reachability_guard.py::test_no_new_truly_dark_package
2026-10-26T21:47:35.1064911Z 21.41s setup    tests/architectural/test_no_manual_global_state_mutation.py::test_no_parse_failures
2026-10-26T21:47:35.1065696Z 20.72s call     tests/architectural/test_inline_meta_read_gate.py::test_fr010_completeness_no_hidden_meta_bypass
2026-10-26T21:47:35.1066400Z 20.59s setup    tests/architectural/test_status_events_writes_gate.py::test_no_out_of_store_writes
2026-10-26T21:47:35.1067225Z 19.94s setup    tests/architectural/test_no_duplicate_suite_execution.py::test_scanned_workflow_set_is_non_empty_and_carries_the_reporting_host
2026-10-26T21:47:35.1068140Z 19.82s setup    tests/architectural/test_no_write_side_rederivation.py::test_adopted_modules_have_no_write_side_rederivation
2026-10-26T21:47:35.1069112Z 19.82s setup    tests/architectural/test_timing_coverage_invariant.py::test_functional_assertion_coverage_does_not_regress[tests/agent/glossary/test_extraction.py]
2026-10-26T21:47:35.1070077Z 17.15s call     tests/architectural/test_inline_meta_read_gate.py::test_inline_meta_read_gate_green_against_seeded_allowlist
2026-10-26T21:47:35.1070849Z 17.06s call     tests/architectural/test_inline_meta_read_gate.py::test_allowlist_entries_are_still_live
2026-10-26T21:47:35.1071516Z 17.00s call     tests/architectural/test_inline_meta_read_gate.py::test_fr010_single_meta_decoder
2026-10-26T21:47:35.1072238Z 16.96s call     tests/architectural/test_inline_meta_read_gate.py::test_fr010_canary_allowed_shapes_do_not_trip
2026-10-26T21:47:35.1073229Z 16.94s call     tests/architectural/test_inline_meta_read_gate.py::test_inline_meta_read_floor
2026-10-26T21:47:35.1073971Z 14.90s call     tests/architectural/test_owned_checkout_single_authority.py::test_g1_resolve_ownership_claim_only_in_minter
2026-10-26T21:47:35.1074733Z 11.92s call     tests/architectural/test_no_dead_modules.py::test_no_package_is_only_imported_by_itself
2026-10-26T21:47:35.1075587Z 10.26s call     tests/architectural/test_no_write_side_rederivation.py::test_adopted_and_residual_modules_have_no_checkout_derived_commit_target
2026-10-26T21:47:35.1076504Z 10.14s call     tests/architectural/test_safe_commit_import_boundary.py::test_safe_commit_destination_ref_shim_is_allowlisted
2026-10-26T21:47:35.1077318Z 10.13s call     tests/architectural/test_safe_commit_import_boundary.py::test_safe_commit_target_argument_is_seam_derived
2026-10-26T21:47:35.1078045Z 9.34s call     tests/architectural/test_no_dead_modules.py::test_no_new_dead_modules_under_src
2026-10-26T21:47:35.1078790Z 9.33s call     tests/architectural/test_owned_checkout_single_authority.py::test_g4_effective_root_identifier_is_banned
2026-10-26T21:47:35.1079617Z 8.92s call     tests/architectural/test_untrusted_path_containment.py::test_main_flags_ghost_when_discovered_sink_disappears
2026-10-26T21:47:35.1080381Z 8.75s call     tests/architectural/test_untrusted_path_containment.py::test_audit_passes_on_fixed_tree
2026-10-26T21:47:35.1081117Z 8.75s call     tests/architectural/test_untrusted_path_containment.py::test_main_flags_injected_undocumented_sink
2026-10-26T21:47:35.1081893Z 8.64s call     tests/architectural/test_untrusted_path_containment.py::test_all_discovered_rows_appear_in_inventory
2026-10-26T21:47:35.1082998Z 8.33s call     tests/architectural/test_safe_commit_import_boundary.py::test_evaluate_has_exactly_the_blessed_importers
2026-10-26T21:47:35.1083756Z 7.78s call     tests/architectural/test_untrusted_path_containment.py::test_discovered_rows_non_empty
2026-10-26T21:47:35.1084662Z 7.76s call     tests/architectural/test_mission_resolver_walker_gate.py::test_no_unsanctioned_raw_kitty_specs_enumeration_in_src
2026-10-26T21:47:35.1085487Z 7.21s call     tests/architectural/test_status_module_boundary.py::test_ast_scan_no_direct_status_imports_repo_wide
2026-10-26T21:47:35.1086258Z 6.22s call     tests/architectural/test_coord_read_residuals_closeout.py::test_fr007_arm_live_identity_scan_is_clean
2026-10-26T21:47:35.1087024Z 5.85s call     tests/architectural/test_status_module_boundary.py::test_the_lenient_event_reader_is_advisory_only
2026-10-26T21:47:35.1087775Z 5.48s call     tests/architectural/test_coord_read_residuals_closeout.py::test_fr007_arm_live_scan_is_non_vacuous
2026-10-26T21:47:35.1088534Z 4.56s call     tests/architectural/test_owned_checkout_single_authority.py::test_g3_mint_referenced_only_in_minter
2026-10-26T21:47:35.1089363Z 4.42s call     tests/architectural/test_owned_checkout_single_authority.py::test_g2_validators_called_only_from_cli_helper_and_minter
2026-10-26T21:47:35.1090242Z 3.56s call     tests/architectural/test_cli_console_single_seam.py::test_cli_layer_builtin_print_carries_no_rich_markup
2026-10-26T21:47:35.1091045Z 2.51s call     tests/architectural/test_lifted_root_no_checklist_surface.py::test_no_checklist_command_string_in_scan_roots
2026-10-26T21:47:35.1091818Z 2.32s call     tests/architectural/test_owned_checkout_single_authority.py::test_g5_no_bare_path_owned_root
2026-10-26T21:47:35.1092715Z 2.05s call     tests/architectural/test_no_duplicate_suite_execution.py::test_mutation4_net_new_workflow_file_is_detected
2026-10-26T21:47:35.1093481Z 1.96s call     tests/architectural/test_no_tmp_paths_in_tests.py::test_no_evasion_roots_in_live_test_corpus
2026-10-26T21:47:35.1094315Z 1.74s call     tests/architectural/test_no_duplicate_suite_execution.py::test_mutation1_the_live_suite_step_is_detected_through_its_own_spelling
2026-10-26T21:47:35.3119034Z 1.73s call     tests/architectural/test_workflow_coherence.py::test_every_restored_filter_glob_is_live
2026-10-26T21:47:35.3120763Z 1.70s call     tests/architectural/test_workflow_coherence.py::test_vestigial_glob_rows_stay_earned
2026-10-26T21:47:35.3122599Z 1.49s call     tests/architectural/test_completion_manifest_freshness.py::test_committed_completion_manifest_matches_live_cli
2026-10-26T21:47:35.3124644Z 1.36s call     tests/architectural/test_no_duplicate_suite_execution.py::test_every_live_workflow_is_classified_and_every_exclusion_is_declared
2026-10-26T21:47:35.3126220Z 1.30s call     tests/architectural/test_no_duplicate_suite_execution.py::test_mutation_control_removing_the_suite_step_clears_the_finding
2026-10-26T21:47:35.3127612Z 1.28s call     tests/architectural/test_cli_console_single_seam.py::test_cli_layer_constructs_no_raw_console
2026-10-26T21:47:35.3128861Z 1.27s call     tests/architectural/test_workflow_coherence.py::test_pytest_workflow_set_equals_model_allowlist_live
2026-10-26T21:47:35.3130207Z 1.26s call     tests/architectural/test_ruff_format_exclude_ratchet.py::test_every_exclude_entry_still_genuinely_reformats
2026-10-26T21:47:35.3131597Z 1.16s call     tests/architectural/test_workflow_coherence.py::test_no_live_workflow_reaches_the_suite_through_an_indirection
2026-10-26T21:47:35.3133103Z 1.12s call     tests/architectural/test_no_duplicate_suite_execution.py::test_mutation2_inlined_suite_command_is_detected
2026-10-26T21:47:35.3134426Z 1.11s call     tests/architectural/test_no_duplicate_suite_execution.py::test_mutation3_script_wrapper_is_detected
2026-10-26T21:47:35.3135602Z 1.09s call     tests/architectural/test_no_duplicate_suite_execution.py::test_mutation3_make_delegation_hop_is_detected
2026-10-26T21:47:35.3136878Z 1.08s call     tests/architectural/test_no_duplicate_suite_execution.py::test_no_blind_runner_form_reaches_pytest_in_ci
2026-10-26T21:47:35.3137841Z 1.05s call     tests/architectural/test_no_tmp_paths_in_tests.py::test_no_shared_tmp_literals_in_live_test_corpus
2026-10-26T21:47:35.3138959Z 1.04s call     tests/architectural/test_no_duplicate_suite_execution.py::test_live_tree_duplicate_set_is_exactly_the_known_set
2026-10-26T21:47:35.3139933Z 1.03s call     tests/architectural/test_docs_cli_reference_parity.py::test_visible_paths_match_reference[0]
2026-10-26T21:47:35.3140934Z 1.01s call     tests/architectural/test_no_duplicate_suite_execution.py::test_every_authorized_ledger_row_still_names_a_live_suite_job
2026-10-26T21:47:35.3141575Z 
2026-10-26T21:47:35.3141713Z (2342 durations < 1s hidden.)
2026-10-26T21:47:35.3142128Z =========================== short test summary info ============================
2026-10-26T21:47:35.3143436Z FAILED tests/architectural/test_status_module_boundary.py::test_ast_scan_no_direct_status_imports_repo_wide - AssertionError: Direct status submodule imports found outside the allow-list (1 violations):
2026-10-26T21:47:35.3144816Z     /home/runner/work/spec-kitty/spec-kitty/src/runtime/next/discovery.py:288: specify_cli.status.review_roles
2026-10-26T21:47:35.3145470Z   
2026-10-26T21:47:35.3145833Z   All imports from status/ must go through `from specify_cli.status import X`.
2026-10-26T21:47:35.3146558Z   To add a temporary exemption: add the file path to _WP10_DEFERRED_FILES with a comment explaining WHY and which WP will fix it.
2026-10-26T21:47:35.3147370Z   Permanent exemptions (C-004 plumbing): coordination/status_transition.py, coordination/transaction.py.
2026-10-26T21:47:35.3148177Z assert not ['/home/runner/work/spec-kitty/spec-kitty/src/runtime/next/discovery.py:288: specify_cli.status.review_roles']
2026-10-26T21:47:35.3148846Z ============= 1 failed, 798 passed, 1 skipped in 243.03s (0:04:03) =============
2026-10-26T21:47:35.6724296Z ##[error]Process completed with exit code 1.
2026-10-26T21:47:35.6795162Z ##[group]Run python3 -m scripts.ci.memory_sampler stop --out "$RUNNER_TEMP/memory-sampler.json"
2026-10-26T21:47:35.6795870Z [36;1mpython3 -m scripts.ci.memory_sampler stop --out "$RUNNER_TEMP/memory-sampler.json"[0m
2026-10-26T21:47:35.6859321Z shell: /usr/bin/bash -e {0}
2026-10-26T21:47:35.6859608Z env:
2026-10-26T21:47:35.6859922Z   UV_PYTHON_INSTALL_DIR: /home/runner/work/_temp/uv-python-dir
2026-10-26T21:47:35.6860358Z   UV_PYTHON: 3.12
2026-10-26T21:47:35.6860647Z   UV_CACHE_DIR: /home/runner/work/_temp/setup-uv-cache
2026-10-26T21:47:35.6860996Z ##[endgroup]
2026-10-26T21:47:35.8447770Z peak_rss_bytes=4636717056 source=meminfo baseline_bytes=1332457472 delta_bytes=3304259584 samples=129 elapsed_s=253.4 cgroup_peak_bytes=5259108352
2026-10-26T21:47:35.8613118Z ##[group]Run actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a
2026-10-26T21:47:35.8613582Z with:
2026-10-26T21:47:35.8613824Z   name: ci-router-architectural-fast-junit
2026-10-26T21:47:35.8614134Z   path: out/reports/
2026-10-26T21:47:35.8614371Z   if-no-files-found: warn
2026-10-26T21:47:35.8614626Z   compression-level: 6
2026-10-26T21:47:35.8614862Z   overwrite: false
2026-10-26T21:47:35.8615086Z   include-hidden-files: false
2026-10-26T21:47:35.8615361Z   archive: true
2026-10-26T21:47:35.8615569Z env:
2026-10-26T21:47:35.8615842Z   UV_PYTHON_INSTALL_DIR: /home/runner/work/_temp/uv-python-dir
2026-10-26T21:47:35.8616185Z   UV_PYTHON: 3.12
2026-10-26T21:47:35.8616441Z   UV_CACHE_DIR: /home/runner/work/_temp/setup-uv-cache
2026-10-26T21:47:35.8616753Z ##[endgroup]
2026-10-26T21:47:36.0313797Z With the provided path, there will be 1 file uploaded
2026-10-26T21:47:36.0323885Z Artifact name is valid!
2026-10-26T21:47:36.0324450Z Root directory input is valid!
2026-10-26T21:47:36.3557805Z Uploading artifact: ci-router-architectural-fast-junit.zip
2026-10-26T21:47:36.3600712Z Beginning upload of artifact content to blob storage
2026-10-26T21:47:36.6251898Z Uploaded bytes 16460
2026-10-26T21:47:36.6767846Z Finished uploading artifact content to blob storage!
2026-10-26T21:47:36.6769386Z SHA256 digest of uploaded artifact is 2e18e7ac39be4f67650a27a2380512c462939feeaa6b1865f9f6283f4728f7f8
2026-10-26T21:47:36.6770356Z Finalizing artifact upload
2026-10-26T21:47:37.2294160Z Artifact ci-router-architectural-fast-junit successfully finalized. Artifact ID 12691038612
2026-10-26T21:47:37.2295764Z Artifact ci-router-architectural-fast-junit has been successfully uploaded! Final size is 16460 bytes. Artifact ID is 12691038612
2026-10-26T21:47:37.2299775Z Artifact download URL: https://github.com/crucible-energy/spec-kitty/actions/runs/40406679253/artifacts/12691038612
2026-10-26T21:47:37.2509412Z Post job cleanup.
2026-10-26T21:47:37.3418663Z [command]/usr/bin/git version
2026-10-26T21:47:37.3472273Z git version 2.55.0
2026-10-26T21:47:37.3521845Z Temporarily overriding HOME='/home/runner/work/_temp/26191cec-59c7-4ada-84d8-74cb0dfa7a84' before making global git config changes
2026-10-26T21:47:37.3524527Z Adding repository directory to the temporary git global config as a safe directory
2026-10-26T21:47:37.3529069Z [command]/usr/bin/git config --global --add safe.directory /home/runner/work/spec-kitty/spec-kitty
2026-10-26T21:47:37.3584844Z [command]/usr/bin/git config --local --name-only --get-regexp core\.sshCommand
2026-10-26T21:47:37.3647223Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
2026-10-26T21:47:37.3939412Z [command]/usr/bin/git config --local --name-only --get-regexp http\.https\:\/\/github\.com\/\.extraheader
2026-10-26T21:47:37.3971282Z http.https://github.com/.extraheader
2026-10-26T21:47:37.3987046Z [command]/usr/bin/git config --local --unset-all http.https://github.com/.extraheader
2026-10-26T21:47:37.4032867Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'http\.https\:\/\/github\.com\/\.extraheader' && git config --local --unset-all 'http.https://github.com/.extraheader' || :"
2026-10-26T21:47:37.4555513Z Cleaning up orphan processes
