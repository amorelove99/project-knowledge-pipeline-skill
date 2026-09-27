---
name: project-knowledge-pipeline
description: >-
  Opt-in capture and reuse of real software project work for GitHub documentation,
  Obsidian knowledge, blog drafts, and video source material. Use only when the
  user requests this pipeline or the current repository has an active
  .project-knowledge/ACTIVE marker. Ignore it for ordinary coding tasks.
---

# Project Knowledge & Publishing Pipeline Skill

Normal development is the primary task. There are only inactive and active states. Do not create pipeline files for ordinary requests. Activate after planning, before implementation, unless the user requests mid-project capture or reconstruction. Do not generate outputs during coding.

Use `python3 <this-skill>/scripts/pkp.py --repo <repo-root> <operation>`. The script is deterministic; you judge which observations are important, verify claims against current files and Git, and edit drafts where needed. Run operations from the repository root when possible. If recording fails, report it and continue safe implementation. A public export privacy block stops the export, not project work.

## Operations

- `start`: inspect repository, status, user changes and context; then run `init`. The marker persists across sessions. If starting mid-project, write a labeled `pre_pipeline_summary` based only on verifiable evidence.
- During active work, append only high-value events with `add-event --json <file>` and meaningful decisions with `add-decision --json <file>`. Update reproducibility facts via `update-repro --json <file>`. Read [capture rules](references/capture-rules.md) and [event schema](references/event-schema.md) when capturing. Never store secrets or private reasoning.
- `status`: run `status`; report concise counts and outputs.
- `finish`: inspect current repo, Git, docs, tests, and evidence. Run `finish`; review the retrospective and correct unsupported claims before treating it as canonical. It does not publish.
- `export github|obsidian|blog|video|all`: run `export <target>` after finishing, then review the generated package using its [target reference](references/github-output.md), [Obsidian](references/obsidian-output.md), [blog](references/blog-output.md), or [video](references/video-output.md). All outputs are local. Public outputs require privacy review. Only copy reviewed GitHub docs into tracked repository paths when requested.
- `verify github`: read [reproducibility](references/reproducibility.md), run `verify github`, and perform feasible fresh-checkout and real application checks. Keep PASS, FAIL, and NOT TESTED distinct.
- `reconstruct`: for an existing project, inspect repository, history, docs and executable evidence, then run `reconstruct`. Fill only verifiable facts; mark missing history unknown.
- `doctor`: run `doctor` for state, JSON, exclusion, config and privacy checks.

The helper takes JSON via `--json PATH` or `--json -` for stdin. Generated drafts are starting points, not proof of successful deployment. Read [privacy rules](references/privacy.md) before capture or public export. Never push, publish, or commit private `.project-knowledge/` data automatically.
