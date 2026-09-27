# Project instructions

This repository is the source for the user-level `project-knowledge-pipeline` Skill. Keep the Skill off by default for unrelated work. Do not activate its own capture merely because this repository contains the Skill source.

Edit `project-knowledge-pipeline/` here, validate with `python3 -m unittest discover -s tests` and the skill-creator quick validator, then copy the validated package to `~/.codex/skills/project-knowledge-pipeline/`. Keep user config, project `.project-knowledge/` data, and vault content out of this repository.

The Python helper uses the standard library. It performs deterministic state and file operations; Codex supplies judgment about which events matter and what prose is supported by evidence. Never infer missing engineering history.
