# Project Knowledge & Publishing Pipeline

An opt-in Codex Skill that records useful engineering evidence while you build, then turns it into local drafts for GitHub, Obsidian, a technical blog, and short-video source material. Its display name is **Project Knowledge & Publishing Pipeline**.

**Capture once, transform many times, publish selectively.** The Skill does not publish anything, create a GitHub repository, or send project records to a service. Normal coding requests leave it off.

## What it does

| Stage | Result |
| --- | --- |
| Start | Creates a private `.project-knowledge/ACTIVE` marker in the target project. |
| Build | Records only significant failures, rejected hypotheses, root causes, decisions, validation, and deployment facts. |
| Finish | Produces a private project retrospective and removes `ACTIVE`. |
| Export | Generates local GitHub documentation, Obsidian notes, blog source/draft, or video source material. |
| Verify | Reports GitHub release checks as `PASS`, `FAIL`, or `NOT TESTED`. |

The Python helper performs deterministic file and state operations. Codex decides what is worth recording and reviews generated claims against the current repository. Drafts are not proof that a project is deployable.

## Requirements

- Codex with local Skill support. The [official OpenAI Skills guide](https://learn.chatgpt.com/docs/build-skills) explains discovery and invocation.
- Python 3.9 or newer for the helper (tested here with Python 3.14).
- Git for project-local exclusion, history inspection, and the fresh-checkout verification. A non-Git directory can use basic local capture, but GitHub release checks need Git.
- Obsidian is optional. No database, daemon, Docker, cloud backend, or API key is required.

## Install

Clone this repository, then copy the Skill directory into a user-level Skills location. The current [Codex documentation](https://learn.chatgpt.com/docs/build-skills) lists `~/.agents/skills`; this project's original local installation uses `~/.codex/skills` and has been discovered by Codex there.

```bash
git clone https://github.com/quqbaku/project-knowledge-pipeline.git
mkdir -p ~/.agents/skills
cp -R project-knowledge-pipeline/project-knowledge-pipeline ~/.agents/skills/
```

If Codex does not show the Skill after installation, restart Codex. To update it later, pull this repository and replace the installed `project-knowledge-pipeline` folder with the reviewed new version. Keep the source repository and installed copy in sync.

## Use it in natural language

You do not need to call the Python script yourself. In a Codex chat rooted in the project you want to record, say for example:

> The plan is ready. Start implementing this macOS service and use Project Knowledge Pipeline to preserve the real development process for later GitHub and blog material.

Codex starts the pipeline in that project, then continues ordinary development. Later you can say:

> Show the pipeline status.

> The project is stable. Finish the record and generate the retrospective.

> Prepare GitHub documentation and verify which release steps have actually been tested.

> Export reusable lessons to Obsidian and produce blog and video source drafts.

Explicit Skill calls are also supported: `$project-knowledge-pipeline start`, `status`, `finish`, `export github|obsidian|blog|video|all`, `verify github`, `reconstruct`, and `doctor`. Start after planning, just before implementation. For an older completed project, ask Codex to reconstruct only what repository and Git evidence support.

## Private records and outputs

In each activated project, the helper creates `.project-knowledge/`. For Git repositories it adds `.project-knowledge/` to that repository's local `.git/info/exclude`, so raw records stay out of ordinary Git status and commits. Do not force-add this directory. It holds JSONL events and decisions, reproducibility facts, an archived session snapshot, and generated drafts.

Only events explicitly marked `public_safe: true` can enter blog and video drafts. Public drafts receive basic home-path, email, and private-host redaction; suspected credentials block export. Mechanical checks cannot recognize every sensitive detail, so review public text before copying it into tracked files or publishing it. Obsidian notes can contain more local context, but should never contain secrets.

GitHub export writes `generated/github/README_DRAFT.md` inside the private directory. Review it and copy suitable text into the public project's normal `README.md` yourself or ask Codex to do so. `verify github` performs a mechanical baseline; installation, startup, core behavior, and restart stay `NOT TESTED` until actually checked.

## Optional Obsidian configuration

Create `~/.codex/project-knowledge-pipeline/config.json` if you want exports copied into a local vault:

```json
{
  "obsidian": {
    "enabled": true,
    "vault_path": "/path/to/your/vault",
    "base_folder": "Engineering"
  }
}
```

Without this config, Obsidian export still generates a local package under `.project-knowledge/generated/obsidian/`. A configured export does not overwrite a different existing vault note.

## Develop and test this Skill

The source of truth is [`project-knowledge-pipeline/`](project-knowledge-pipeline/). The helper uses only the Python standard library. Run:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile project-knowledge-pipeline/scripts/pkp.py
```

The tests use disposable Git repositories and a disposable vault; they do not write to your real Obsidian vault. See [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) and [`docs/DECISIONS.md`](docs/DECISIONS.md) for architecture and decisions.

## Current limits

- Output text is a draft that Codex and the project owner must review for accuracy and privacy.
- The helper does not automatically commit, push, create public repositories, publish posts, or make videos.
- `reconstruct` cannot recover uncommitted experiments or conversations absent from the repository.
- Python 3.9+ syntax is required, but the automated suite has only been run on the local Python version reported above.

MIT licensed. See [`LICENSE`](LICENSE).
