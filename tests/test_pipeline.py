import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "project-knowledge-pipeline" / "scripts" / "pkp.py"


class PipelineWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / "sample-project"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        (self.repo / "README.md").write_text("# Sample\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "README.md"], check=True)
        self.home = self.base / "home"
        self.home.mkdir()

    def run_pkp(self, *args, payload=None, ok=True):
        env = {**os.environ, "HOME": str(self.home)}
        proc = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo), *args],
                              input=json.dumps(payload) if payload is not None else None,
                              text=True, capture_output=True, env=env)
        if ok:
            self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc

    def test_off_by_default_and_private_activation(self):
        self.assertIn("OFF", self.run_pkp("status").stdout)
        self.assertFalse((self.repo / ".project-knowledge").exists())
        self.run_pkp("init")
        self.assertTrue((self.repo / ".project-knowledge" / "ACTIVE").exists())
        ignored = subprocess.run(["git", "-C", str(self.repo), "check-ignore", "-q", ".project-knowledge/state.json"])
        self.assertEqual(ignored.returncode, 0)
        status = subprocess.run(["git", "-C", str(self.repo), "status", "--short"], capture_output=True, text=True)
        self.assertNotIn(".project-knowledge", status.stdout)
        self.assertIn("ACTIVE", self.run_pkp("status").stdout)

    def test_capture_finish_and_all_exports(self):
        self.run_pkp("init")
        event = {"type": "failure", "title": "Adapter request failed", "observation": "Local request failed", "hypothesis": "Port mismatch", "evidence": "Endpoint answered", "result": "Cause unknown", "content_value": "medium", "public_safe": True}
        self.run_pkp("add-event", "--json", "-", payload=event)
        correction = {"type": "rejected_hypothesis", "title": "Port ruled out", "observation": "Endpoint answered", "evidence": "Direct request succeeded", "result": "Port hypothesis rejected", "public_safe": True}
        self.run_pkp("add-event", "--json", "-", payload=correction)
        root = {"type": "root_cause", "title": "API contract mismatch", "observation": "Schemas differed", "evidence": "Request and response comparison", "result": "Adapter fixed integration", "content_value": "high", "public_safe": True}
        self.run_pkp("add-event", "--json", "-", payload=root)
        self.run_pkp("add-event", "--json", "-", payload={"type": "failure", "title": "Private detail", "observation": "Private context", "evidence": "Private evidence", "result": "Private result"})
        self.run_pkp("add-decision", "--json", "-", payload={"decision": "Use adapter", "reason": "Keep validated model"})
        self.run_pkp("update-repro", "--json", "-", payload={"platforms": ["macOS"], "required_env_names": ["ASR_ENDPOINT"], "verification_commands": ["python3 -m unittest"]})
        self.run_pkp("finish")
        self.assertFalse((self.repo / ".project-knowledge" / "ACTIVE").exists())
        retrospective = (self.repo / ".project-knowledge/generated/retrospective/PROJECT_RETROSPECTIVE.md").read_text()
        self.assertIn("Port hypothesis rejected", retrospective)
        self.assertIn("API contract mismatch", retrospective)
        self.run_pkp("export", "all")
        d = self.repo / ".project-knowledge/generated"
        for path in ("github/README_DRAFT.md", "github/.env.example", "obsidian/Projects/sample-project.md", "obsidian/Problems/API contract mismatch.md", "blog/BLOG_SOURCE.md", "blog/BLOG_DRAFT.md", "video/VIDEO_SOURCE.md"):
            self.assertTrue((d / path).exists(), path)
        self.assertFalse((self.repo / "README_DRAFT.md").exists())
        self.assertIn("[[Problems/API contract mismatch|API contract mismatch]]", (d / "obsidian/Projects/sample-project.md").read_text())
        self.assertIn("API contract mismatch", (d / "blog/BLOG_SOURCE.md").read_text())
        self.assertNotIn("Private detail", (d / "blog/BLOG_SOURCE.md").read_text())
        self.assertNotIn("Private detail", (d / "video/VIDEO_SOURCE.md").read_text())
        self.run_pkp("verify", "github")
        verification = (d / "github/RELEASE_VERIFICATION.md").read_text()
        self.assertIn("Startup: NOT TESTED", verification)
        self.assertIn("Secret scan: PASS", verification)
        self.assertIn("PASS", self.run_pkp("doctor").stdout)

    def test_capture_rejects_secret_and_public_path_is_sanitized(self):
        self.run_pkp("init")
        sample_value = "abcdefgh" + "ijklmnop"
        bad = {"type": "failure", "title": "Bad", "observation": "api_key=" + sample_value, "evidence": "test", "result": "test"}
        proc = self.run_pkp("add-event", "--json", "-", payload=bad, ok=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn(sample_value, proc.stderr)
        self.run_pkp("update-repro", "--json", "-", payload={"install_commands": ["cd /Users/example/project && make"]})
        self.run_pkp("finish")
        self.run_pkp("export", "github")
        content = (self.repo / ".project-knowledge/generated/github/README_DRAFT.md").read_text()
        self.assertNotIn("/Users/example", content)

    def test_reconstruct_does_not_activate(self):
        self.run_pkp("reconstruct")
        self.assertFalse((self.repo / ".project-knowledge/ACTIVE").exists())
        content = (self.repo / ".project-knowledge/generated/retrospective/RECONSTRUCTION_EVIDENCE.md").read_text()
        self.assertIn("Unrecorded failures", content)
        self.assertTrue((self.repo / ".project-knowledge/generated/retrospective/PROJECT_RETROSPECTIVE.md").exists())

    def test_configured_obsidian_copy_and_real_fresh_checkout(self):
        vault = self.base / "vault"
        vault.mkdir()
        config = self.home / ".codex/project-knowledge-pipeline/config.json"
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"obsidian": {"enabled": True, "vault_path": str(vault), "base_folder": "Engineering"}}))
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-q", "-m", "Initial", "--no-gpg-sign"], check=True)
        self.run_pkp("init")
        self.run_pkp("finish")
        self.run_pkp("export", "obsidian")
        self.assertTrue((vault / "Engineering/Projects/sample-project.md").exists())
        self.run_pkp("verify", "github")
        report = (self.repo / ".project-knowledge/generated/github/RELEASE_VERIFICATION.md").read_text()
        self.assertIn("Fresh checkout: PASS", report)


if __name__ == "__main__":
    unittest.main()
