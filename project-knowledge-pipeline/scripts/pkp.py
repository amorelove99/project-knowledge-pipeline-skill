#!/usr/bin/env python3
"""Deterministic local state and draft generation for project-knowledge-pipeline."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DATA = ".project-knowledge"
REPRO_KEYS = (
    "platforms", "architectures", "runtime_versions", "package_managers", "dependencies",
    "system_dependencies", "required_env_names", "ports", "permissions", "network_requirements",
    "config_files", "service_manager", "install_commands", "start_commands", "stop_commands",
    "verification_commands", "known_failures", "validated_environments",
)
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----"),
    "credential assignment": re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|secret|password|cookie)\s*[:=]\s*['\"]?(?!<|your_|example|placeholder|\$\{)[A-Za-z0-9_./+\-=]{12,}"),
    "token": re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
}
HOME_PATH = re.compile(r"/(?:Users|home)/[^/\s]+")
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PRIVATE_IP = re.compile(r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b")
PRIVATE_HOST = re.compile(r"\b[a-zA-Z0-9.-]+\.(?:local|internal)\b")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def git(repo: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else ""


def root_for(path: Path) -> Path:
    path = path.resolve()
    root = git(path, "rev-parse", "--show-toplevel")
    return Path(root) if root else path


def data_dir(repo: Path) -> Path:
    return repo / DATA


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_record(path: Path, item: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as out:
        out.write(json.dumps(item, ensure_ascii=False) + "\n")


def secret_categories(text: str) -> list[str]:
    return [name for name, pattern in SECRET_PATTERNS.items() if pattern.search(text)]


def public_text(value: str) -> str:
    value = HOME_PATH.sub("~", value)
    value = EMAIL.sub("[email redacted]", value)
    value = PRIVATE_IP.sub("[private IP]", value)
    return PRIVATE_HOST.sub("[private host]", value)


def safe_write(path: Path, content: str, public: bool = False) -> None:
    categories = secret_categories(content)
    if categories:
        raise ValueError("possible secret detected: " + ", ".join(categories))
    if public:
        content = public_text(content)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def require_data(repo: Path) -> Path:
    d = data_dir(repo)
    if not (d / "state.json").exists():
        raise ValueError("pipeline not initialized; use start")
    return d


def ensure_excluded(repo: Path) -> None:
    if not git(repo, "rev-parse", "--show-toplevel"):
        return
    exclude = repo / ".git" / "info" / "exclude"
    git_dir = git(repo, "rev-parse", "--git-dir")
    if git_dir:
        exclude = (repo / git_dir / "info" / "exclude").resolve()
    exclude.parent.mkdir(parents=True, exist_ok=True)
    current = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    if DATA + "/" not in current.splitlines():
        exclude.write_text(current.rstrip("\n") + "\n" + DATA + "/\n", encoding="utf-8")


def default_repro() -> dict:
    return {k: ({} if k in {"runtime_versions", "package_managers"} else None if k == "service_manager" else []) for k in REPRO_KEYS}


def init(repo: Path) -> None:
    d = data_dir(repo)
    if (d / "state.json").exists():
        raise ValueError("pipeline already initialized")
    if git(repo, "ls-files", DATA):
        raise ValueError("private pipeline directory is already tracked by Git")
    ensure_excluded(repo)
    d.mkdir(exist_ok=True)
    (d / "ACTIVE").write_text(now() + "\n", encoding="utf-8")
    write_json(d / "state.json", {"project": repo.name, "started": now(), "finished": None, "status": "ACTIVE"})
    write_json(d / "reproducibility.json", default_repro())
    print("Pipeline: ACTIVE")
    print("Private data: " + str(d))


def status(repo: Path) -> None:
    d = data_dir(repo)
    if not (d / "state.json").exists():
        print("Pipeline: OFF")
        return
    state = read_json(d / "state.json", {})
    events = records(d / "events.jsonl")
    print("Pipeline:", "ACTIVE" if (d / "ACTIVE").exists() else "FINISHED")
    print("Project:", state.get("project", repo.name))
    print("Events:", len(events), "Decisions:", len(records(d / "decisions.jsonl")))
    print("Started:", state.get("started", "unknown"))
    print("Current branch:", git(repo, "branch", "--show-current") or "none")
    print("Last event:", events[-1].get("title", "none") if events else "none")
    for target in ("github", "obsidian", "blog", "video"):
        p = d / "generated" / target
        print(target.title() + ":", "Generated" if p.exists() and any(p.iterdir()) else "Not generated")


def input_object(path: str) -> dict:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    if secret_categories(raw):
        raise ValueError("possible secret detected in input: " + ", ".join(secret_categories(raw)))
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("input must be a JSON object")
    return obj


def add(repo: Path, kind: str, item: dict) -> None:
    d = require_data(repo)
    if not (d / "ACTIVE").exists():
        raise ValueError("pipeline is finished; start a new session before capture")
    mandatory = ("type", "title", "observation", "evidence", "result") if kind == "event" else ("decision", "reason")
    for key in mandatory:
        if not isinstance(item.get(key), str) or not item[key].strip():
            raise ValueError("missing field: " + key)
    filename, prefix = ("events.jsonl", "EVT") if kind == "event" else ("decisions.jsonl", "DEC")
    path = d / filename
    item.pop("id", None)
    item.pop("timestamp", None)
    item = {"id": f"{prefix}-{len(records(path)) + 1:04d}", "timestamp": now(), **item}
    append_record(path, item)
    print(item["id"] + " recorded")


def update_repro(repo: Path, item: dict) -> None:
    d = require_data(repo)
    if not (d / "ACTIVE").exists():
        raise ValueError("pipeline is finished")
    unknown = set(item) - set(REPRO_KEYS)
    if unknown:
        raise ValueError("unknown reproducibility fields: " + ", ".join(sorted(unknown)))
    current = read_json(d / "reproducibility.json", default_repro())
    current.update(item)
    write_json(d / "reproducibility.json", current)
    print("Reproducibility updated")


def repo_facts(repo: Path) -> dict:
    tracked = git(repo, "ls-files").splitlines()
    return {
        "branch": git(repo, "branch", "--show-current") or "none",
        "head": git(repo, "rev-parse", "--short", "HEAD") or "uncommitted",
        "recent_commits": git(repo, "log", "-8", "--pretty=format:%h %s").splitlines(),
        "tracked_files": [p for p in tracked if not p.startswith(DATA + "/")][:100],
        "working_changes": git(repo, "status", "--short").splitlines()[:100],
    }


def section(title: str, lines: list[str]) -> str:
    return "## " + title + "\n\n" + ("\n".join(lines) if lines else "Not recorded.") + "\n\n"


def event_lines(events: list[dict], *types: str) -> list[str]:
    return [f"- **{e.get('title', 'Untitled')}** ({e.get('id', '?')}): {e.get('result', '')} Evidence: {e.get('evidence', '')}" for e in events if e.get("type") in types]


def retrospective(repo: Path) -> str:
    d = require_data(repo)
    state = read_json(d / "state.json", {})
    events = records(d / "events.jsonl")
    decisions = records(d / "decisions.jsonl")
    repro = read_json(d / "reproducibility.json", default_repro())
    facts = repo_facts(repo)
    result = "# Project Retrospective\n\nGenerated from recorded evidence. Review claims against current code and behavior.\n\n"
    result += section("Goal", [state.get("goal", "Not recorded.")])
    result += section("Final Result", [f"Repository HEAD: {facts['head']}; branch: {facts['branch']}.", "Actual deployment outcome requires manual verification."])
    result += section("Final Architecture", ["Inspect current repository files: " + ", ".join(facts["tracked_files"][:25]) if facts["tracked_files"] else "Not documented."])
    result += section("Development Timeline", [f"- {e['timestamp']} — {e['title']} ({e['type']})" for e in events])
    result += section("Important Failures", event_lines(events, "failure"))
    result += section("Rejected Approaches", event_lines(events, "rejected_hypothesis"))
    result += section("Root Causes", event_lines(events, "root_cause"))
    result += section("Key Decisions", [f"- {x['decision']} — {x['reason']}" for x in decisions])
    result += section("User Decisions", event_lines(events, "user_decision"))
    result += section("Reproducibility Requirements", [f"- {k}: {json.dumps(v, ensure_ascii=False)}" for k, v in repro.items() if v])
    result += section("Validation", event_lines(events, "validation"))
    result += section("Remaining Limitations", ["Review known failures: " + "; ".join(map(str, repro.get("known_failures", []))) if repro.get("known_failures") else "Not recorded; this does not prove none exist."])
    result += section("Lessons Learned", event_lines(events, "root_cause", "rejected_hypothesis"))
    result += section("Reusable Patterns", event_lines(events, "technical_decision", "architecture_change"))
    result += section("Potential Publishing Assets", [f"- {x.get('description', '')}" for x in records(d / "assets.jsonl")])
    return result


def finish(repo: Path) -> None:
    d = require_data(repo)
    if not (d / "ACTIVE").exists():
        raise ValueError("pipeline already finished")
    output = d / "generated" / "retrospective" / "PROJECT_RETROSPECTIVE.md"
    safe_write(output, retrospective(repo))
    state = read_json(d / "state.json", {})
    state.update({"finished": now(), "status": "FINISHED", "final_head": git(repo, "rev-parse", "HEAD") or None})
    archive = d / "archive" / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    archive.mkdir(parents=True)
    for name in ("state.json", "events.jsonl", "decisions.jsonl", "reproducibility.json", "assets.jsonl"):
        if (d / name).exists():
            shutil.copy2(d / name, archive / name)
    write_json(d / "state.json", state)
    (d / "ACTIVE").unlink()
    print("Pipeline: FINISHED")
    print(output)


def require_finished(repo: Path) -> Path:
    d = require_data(repo)
    if (d / "ACTIVE").exists():
        raise ValueError("finish the active session before exporting")
    return d


def github_export(repo: Path) -> list[Path]:
    d = require_finished(repo)
    repro = read_json(d / "reproducibility.json", default_repro())
    out = d / "generated" / "github"
    lines = ["# " + repo.name, "", "Draft for a reproducible GitHub release. Review against the current repository before publishing.", "", "## Purpose", "", "NOT DOCUMENTED", "", "## Supported environment", ""]
    for key in ("platforms", "architectures", "runtime_versions", "validated_environments"):
        lines.append(f"- {key.replace('_', ' ').title()}: {repro.get(key) or 'NOT TESTED'}")
    for heading, key in (("Prerequisites", "dependencies"), ("System dependencies", "system_dependencies"), ("Installation", "install_commands"), ("Startup", "start_commands"), ("Verification", "verification_commands"), ("Known failures", "known_failures")):
        lines.extend(["", "## " + heading, ""])
        values = repro.get(key) or []
        lines.extend(["- " + str(v) for v in values] if values else ["NOT DOCUMENTED"])
    lines.extend(["", "## Configuration", "", "Required environment variable names: " + (", ".join(repro.get("required_env_names", [])) or "None recorded"), "", "## Removal and update", "", "NOT DOCUMENTED", ""])
    readme = out / "README_DRAFT.md"
    env = out / ".env.example"
    content = "\n".join(lines)
    names = repro.get("required_env_names") or []
    if names:
        if any(not re.fullmatch(r"[A-Z][A-Z0-9_]*", name) for name in names):
            raise ValueError("invalid environment variable name")
    if secret_categories(content):
        raise ValueError("possible secret detected in GitHub draft")
    safe_write(readme, content, public=True)
    paths = [readme]
    if names:
        safe_write(env, "".join(name + "=\n" for name in names), public=True)
        paths.append(env)
    return paths


def blog_export(repo: Path) -> list[Path]:
    d = require_finished(repo)
    events = [e for e in records(d / "events.jsonl") if e.get("public_safe") is True]
    out = d / "generated" / "blog"
    source = "# Blog Source\n\nFactual event record; verify current code before publication.\n\n"
    for e in events:
        source += f"## {e['title']} ({e['id']})\n\nType: {e['type']}\n\nObservation: {e['observation']}\n\nHypothesis: {e.get('hypothesis', 'Not recorded')}\n\nEvidence: {e['evidence']}\n\nResult: {e['result']}\n\n"
    draft = "# " + repo.name + ": development notes\n\nThis is a draft grounded in recorded project events.\n\n"
    for title, kinds in (("Why I built this", ("scope_change", "user_decision")), ("What went wrong", ("failure",)), ("What changed my understanding", ("rejected_hypothesis",)), ("Root cause", ("root_cause",)), ("Final approach", ("technical_decision", "architecture_change")), ("Validated result", ("validation",))):
        draft += section(title, event_lines(events, *kinds))
    draft += section("What I learned", event_lines(events, "root_cause", "rejected_hypothesis"))
    paths = [out / "BLOG_SOURCE.md", out / "BLOG_DRAFT.md"]
    for path, content in zip(paths, (source, draft)):
        safe_write(path, content, public=True)
    return paths


def video_export(repo: Path) -> list[Path]:
    d = require_finished(repo)
    events = [e for e in records(d / "events.jsonl") if e.get("public_safe") is True]
    assets = [a for a in records(d / "assets.jsonl") if a.get("public_safe") is True]
    content = "# Video Source Material\n\nEvidence-backed candidates only; no script or publication.\n\n"
    for title, kinds in (("Possible hooks", ("failure", "root_cause")), ("Main conflict", ("failure",)), ("Wrong assumption", ("rejected_hypothesis",)), ("Turning point", ("root_cause",)), ("Final solution", ("technical_decision", "architecture_change")), ("Demo opportunities", ("validation",))):
        content += section(title, event_lines(events, *kinds))
    content += section("Screenshot and recording opportunities", ["- " + str(a.get("description", "")) for a in assets])
    path = d / "generated" / "video" / "VIDEO_SOURCE.md"
    safe_write(path, content, public=True)
    return [path]


def config_path() -> Path:
    return Path.home() / ".codex" / "project-knowledge-pipeline" / "config.json"


def obsidian_export(repo: Path) -> list[Path]:
    d = require_finished(repo)
    events = records(d / "events.jsonl")
    out = d / "generated" / "obsidian"
    project = out / "Projects" / (repo.name + ".md")
    content = f"---\ntype: project\nstatus: finished\n---\n# {repo.name}\n\n"
    content += section("Project", ["See current repository and the private retrospective for architecture and results."])
    content += section("Important events", event_lines(events, "failure", "root_cause", "technical_decision", "user_decision", "validation"))
    paths = [project]
    links = []
    important = [e for e in events if e.get("content_value") in ("medium", "high")]
    for e in important:
        if e.get("type") not in ("root_cause", "technical_decision", "architecture_change"):
            continue
        folder = "Problems" if e["type"] == "root_cause" else "Patterns"
        name = re.sub(r"[^\w -]", "", e["title"]).strip()[:80] or e["id"]
        path = out / folder / (name + ".md")
        note = f"---\ntype: {folder[:-1].lower()}\nsource_project: {repo.name}\n---\n# {e['title']}\n\nObservation: {e['observation']}\n\nEvidence: {e['evidence']}\n\nResult: {e['result']}\n"
        safe_write(path, note)
        paths.append(path)
        links.append(f"- [[{folder}/{name}|{e['title']}]]")
    content += section("Reusable notes", links)
    safe_write(project, content)
    cfg = read_json(config_path(), {})
    obs = cfg.get("obsidian", {})
    if obs.get("enabled") and obs.get("vault_path"):
        vault = Path(obs["vault_path"]).expanduser().resolve()
        if not vault.is_dir():
            raise ValueError("configured Obsidian vault does not exist")
        base = obs.get("base_folder", "Engineering")
        if Path(base).is_absolute() or ".." in Path(base).parts:
            raise ValueError("invalid Obsidian base folder")
        for path in paths:
            destination = vault / base / path.relative_to(out)
            if destination.exists() and destination.read_text(encoding="utf-8") != path.read_text(encoding="utf-8"):
                raise ValueError("Obsidian note already exists with different content: " + destination.name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        print("Copied to configured Obsidian vault")
    else:
        print("Obsidian vault not configured; local package generated")
    return paths


def verify_github(repo: Path) -> None:
    d = require_finished(repo)
    out = d / "generated" / "github"
    report = out / "RELEASE_VERIFICATION.md"
    checks = {"Fresh checkout": "NOT TESTED", "Installation": "NOT TESTED", "Configuration": "NOT TESTED", "Startup": "NOT TESTED", "Core functionality": "NOT TESTED", "Restart persistence": "NOT TESTED", "Documentation commands": "NOT TESTED", "Secret scan": "NOT TESTED"}
    if git(repo, "rev-parse", "--show-toplevel"):
        tracked = git(repo, "ls-files").splitlines()
        head = git(repo, "rev-parse", "HEAD")
        if head:
            with tempfile.TemporaryDirectory(prefix="pkp-checkout-") as temporary:
                clone = Path(temporary) / "checkout"
                result = subprocess.run(["git", "clone", "--quiet", "--no-local", str(repo), str(clone)], capture_output=True)
                checks["Fresh checkout"] = "PASS" if result.returncode == 0 and git(clone, "rev-parse", "HEAD") == head else "FAIL"
        findings = []
        skipped = False
        for name in tracked:
            path = repo / name
            if path.is_file() and path.stat().st_size < 1_000_000:
                try:
                    findings.extend(secret_categories(path.read_text(encoding="utf-8")))
                except UnicodeError:
                    skipped = True
            else:
                skipped = True
        checks["Secret scan"] = "FAIL" if findings else "NOT TESTED" if skipped else "PASS"
    if out.exists():
        for path in out.glob("*.md"):
            if path != report and secret_categories(path.read_text(encoding="utf-8")):
                checks["Secret scan"] = "FAIL"
    text = "# GitHub Release Verification\n\nMechanical baseline only. Perform real deployment checks before changing NOT TESTED to PASS.\n\n"
    text += "\n".join(f"- {name}: {value}" for name, value in checks.items()) + "\n"
    safe_write(report, text)
    print(report)


def reconstruct(repo: Path) -> None:
    d = data_dir(repo)
    if (d / "state.json").exists():
        raise ValueError("pipeline already initialized")
    if git(repo, "ls-files", DATA):
        raise ValueError("private pipeline directory is already tracked by Git")
    ensure_excluded(repo)
    d.mkdir(exist_ok=True)
    facts = repo_facts(repo)
    write_json(d / "state.json", {"project": repo.name, "started": now(), "finished": now(), "status": "RECONSTRUCTED", "source": "repository-and-git-only"})
    write_json(d / "reproducibility.json", default_repro())
    content = "# Reconstruction Evidence\n\nRepository and Git evidence only. Unrecorded failures, reasoning, and conversations remain unknown.\n\n"
    content += section("Repository snapshot", [f"- Branch: {facts['branch']}", f"- HEAD: {facts['head']}"])
    content += section("Recent commits", ["- " + x for x in facts["recent_commits"]])
    content += section("Tracked files", ["- " + x for x in facts["tracked_files"]])
    content += section("Working changes", ["- " + x for x in facts["working_changes"]])
    safe_write(d / "generated" / "retrospective" / "RECONSTRUCTION_EVIDENCE.md", content)
    safe_write(d / "generated" / "retrospective" / "PROJECT_RETROSPECTIVE.md", retrospective(repo))
    print("Reconstruction baseline created; review evidence and fill facts manually")


def doctor(repo: Path) -> int:
    d = data_dir(repo)
    if not d.exists():
        print("Pipeline: OFF; no private data")
        return 0
    errors = []
    for name in ("state.json", "reproducibility.json"):
        try:
            read_json(d / name, {})
        except (json.JSONDecodeError, UnicodeError):
            errors.append(name + " invalid JSON")
    for name in ("events.jsonl", "decisions.jsonl", "assets.jsonl"):
        try:
            records(d / name)
        except (json.JSONDecodeError, UnicodeError):
            errors.append(name + " invalid JSONL")
    if git(repo, "rev-parse", "--show-toplevel"):
        p = subprocess.run(["git", "-C", str(repo), "check-ignore", "-q", DATA + "/state.json"])
        if p.returncode != 0:
            errors.append("Git exclusion missing")
    state = read_json(d / "state.json", {})
    if (d / "ACTIVE").exists() != (state.get("status") == "ACTIVE"):
        errors.append("ACTIVE marker and state disagree")
    for path in d.rglob("*"):
        if path.is_file() and path.suffix in (".md", ".json", ".jsonl"):
            if secret_categories(path.read_text(encoding="utf-8")):
                errors.append("possible secret in " + path.name)
    cfg = read_json(config_path(), {})
    obs = cfg.get("obsidian", {})
    print("Obsidian:", "configured" if obs.get("enabled") and obs.get("vault_path") else "not configured")
    if obs.get("enabled") and obs.get("vault_path") and not Path(obs["vault_path"]).expanduser().is_dir():
        errors.append("configured Obsidian vault missing")
    print("Doctor:", "PASS" if not errors else "FAIL")
    for issue in errors:
        print("- " + issue)
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "status", "finish", "reconstruct", "doctor"):
        subs.add_parser(name)
    for name in ("add-event", "add-decision", "update-repro"):
        subs.add_parser(name).add_argument("--json", required=True)
    export = subs.add_parser("export")
    export.add_argument("target", choices=("github", "obsidian", "blog", "video", "all"))
    verify = subs.add_parser("verify")
    verify.add_argument("target", choices=("github",))
    args = parser.parse_args()
    repo = root_for(args.repo)
    try:
        if args.command == "init": init(repo)
        elif args.command == "status": status(repo)
        elif args.command == "add-event": add(repo, "event", input_object(args.json))
        elif args.command == "add-decision": add(repo, "decision", input_object(args.json))
        elif args.command == "update-repro": update_repro(repo, input_object(args.json))
        elif args.command == "finish": finish(repo)
        elif args.command == "reconstruct": reconstruct(repo)
        elif args.command == "doctor": return doctor(repo)
        elif args.command == "verify": verify_github(repo)
        elif args.command == "export":
            targets = ("github", "obsidian", "blog", "video") if args.target == "all" else (args.target,)
            for target in targets:
                paths = {"github": github_export, "obsidian": obsidian_export, "blog": blog_export, "video": video_export}[target](repo)
                print(target + ": " + ", ".join(str(p) for p in paths))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
