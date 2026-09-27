# Project context

The Skill provides two project states: inactive and active. A project-local `.project-knowledge/ACTIVE` marker persists capture across Codex sessions. The directory is private and excluded through `.git/info/exclude` for Git repositories. Only significant evidence is recorded while implementation continues.

At completion, `finish` generates a private retrospective and removes the marker. Exports build local output packages from current repository facts and the recorded evidence. Public-facing material is scanned and sanitized before writing; generated content is never published by the helper. Obsidian export writes a local package and, only when configured, copies selected notes to the vault.

`project-knowledge-pipeline/scripts/pkp.py` owns JSON state, append-only records, generated drafts, exclusion checks, and mechanical verification. `SKILL.md` owns trigger boundaries, evidence judgment, and review obligations.
