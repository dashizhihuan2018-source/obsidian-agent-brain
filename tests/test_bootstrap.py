"""Run with: python3 -m unittest discover -s tests -v."""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bootstrap.py"


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.vault = self.base / "个人 大脑"

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--vault", str(self.vault), *args],
            capture_output=True, text=True, encoding="utf-8",
        )

    def require_script(self):
        self.assertTrue(SCRIPT.is_file(), "missing safe vault initializer")

    def test_preview_is_read_only(self):
        self.require_script()
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.vault.exists())
        self.assertEqual(list(self.base.iterdir()), [])
        self.assertIn("首页.md", result.stdout)

    def test_apply_creates_complete_vault_and_local_entry(self):
        self.require_script()
        result = self.run_cli("--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = ["首页.md", "使用指南.md", "AGENTS.md",
                    "90-智能体记忆/记忆规则.md", "90-智能体记忆/MEMORY.md",
                    "90-智能体记忆/TODO.md", "90-智能体记忆/接入说明.md",
                    "90-智能体记忆/待合并/说明.md", "99-模板/项目模板.md"]
        for name in expected:
            self.assertTrue((self.vault / name).is_file(), name)
        content = (self.vault / "90-智能体记忆/接入说明.md").read_text(encoding="utf-8")
        self.assertIn(str(self.vault.resolve()), content)
        for path in self.vault.rglob("*.md"):
            self.assertNotIn("{{VAULT_ROOT}}", path.read_text(encoding="utf-8"))
        self.assertFalse((self.vault / ".obsidian").exists())
        self.assertFalse((self.vault / ".git").exists())

    def test_existing_vault_is_unchanged(self):
        self.require_script()
        self.vault.mkdir()
        sentinel = self.vault / "MEMORY.md"
        sentinel.write_text("private original", encoding="utf-8")
        result = self.run_cli("--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sentinel.read_text(), "private original")
        self.assertEqual(list(self.vault.iterdir()), [sentinel])

    def test_existing_empty_folder_is_refused(self):
        self.require_script()
        self.vault.mkdir()
        self.assertNotEqual(self.run_cli("--apply").returncode, 0)
        self.assertEqual(list(self.vault.iterdir()), [])

    def test_second_run_never_overwrites_notes(self):
        self.require_script()
        self.assertEqual(self.run_cli("--apply").returncode, 0)
        memory = self.vault / "90-智能体记忆/MEMORY.md"
        memory.write_text("user edit", encoding="utf-8")
        self.assertNotEqual(self.run_cli("--apply").returncode, 0)
        self.assertEqual(memory.read_text(), "user edit")

    def test_file_target_is_refused(self):
        self.require_script()
        self.vault.write_text("keep", encoding="utf-8")
        self.assertNotEqual(self.run_cli("--apply").returncode, 0)
        self.assertEqual(self.vault.read_text(), "keep")

    @unittest.skipIf(os.name == "nt", "symlink privileges vary on Windows")
    def test_symlink_target_and_ancestor_are_refused(self):
        self.require_script()
        real = self.base / "real"
        real.mkdir()
        self.vault.symlink_to(real, target_is_directory=True)
        self.assertNotEqual(self.run_cli("--apply").returncode, 0)
        self.vault = self.vault / "new-vault"
        self.assertNotEqual(self.run_cli("--apply").returncode, 0)
        self.assertEqual(list(real.iterdir()), [])

    def test_missing_parent_is_refused_without_creating_it(self):
        self.require_script()
        self.vault = self.base / "missing-parent" / "brain"
        self.assertNotEqual(self.run_cli("--apply").returncode, 0)
        self.assertFalse(self.vault.parent.exists())

    def test_newline_in_path_is_refused(self):
        self.require_script()
        self.vault = self.base / "brain\nextra instruction"
        self.assertNotEqual(self.run_cli("--apply").returncode, 0)
        self.assertFalse(self.vault.exists())

    def test_relative_path_is_refused(self):
        self.require_script()
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--vault", "relative-brain", "--apply"],
            cwd=self.base, capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.base.iterdir()), [])

    def test_help_does_not_require_vault_or_write_files(self):
        self.require_script()
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"], cwd=self.base,
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(self.base.iterdir()), [])

    @unittest.skipIf(os.name == "nt", "symlink privileges vary on Windows")
    def test_dangling_symlink_is_refused(self):
        self.require_script()
        self.vault.symlink_to(self.base / "absent", target_is_directory=True)
        self.assertNotEqual(self.run_cli("--apply").returncode, 0)
        self.assertTrue(self.vault.is_symlink())
        self.assertFalse((self.base / "absent").exists())

    def test_assets_have_no_machine_specific_paths(self):
        assets = ROOT / "assets" / "vault"
        self.assertTrue(assets.is_dir(), "missing portable vault assets")
        for path in assets.rglob("*.md"):
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("/Users/", content, str(path))
            self.assertNotIn("C:\\Users\\", content, str(path))


class ResourceLinkTests(unittest.TestCase):
    def test_all_template_wikilinks_resolve_inside_template_vault(self):
        assets = ROOT / "assets/vault"
        self.assertTrue(assets.is_dir())
        for source in assets.rglob("*.md"):
            for raw in re.findall(r"\[\[([^\]]+)\]\]", source.read_text(encoding="utf-8")):
                target = raw.split("|", 1)[0].split("#", 1)[0]
                if target:
                    self.assertTrue((assets / (target + ".md")).is_file(), f"{source.name}: {raw}")

    def test_all_local_markdown_resource_links_exist(self):
        for source in ROOT.rglob("*.md"):
            for raw in re.findall(r"\[[^\]]*\]\(([^)]+)\)", source.read_text(encoding="utf-8")):
                if "://" not in raw and not raw.startswith("#"):
                    target = raw.split("#", 1)[0]
                    self.assertTrue((source.parent / target).exists(), f"{source.name}: {raw}")


if __name__ == "__main__":
    unittest.main()
