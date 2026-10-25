import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_notes.py"
spec = importlib.util.spec_from_file_location("check_notes", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ScopedCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.vault = self.root / "vault"
        self.vault.mkdir()

    def note(self, name, content):
        path = self.vault / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_exact_links_alias_anchor_embed_and_relative(self):
        self.note("首页.md", "[[folder/目标#概要|目标]] ![[asset.svg]] [[#本页]]")
        self.note("folder/目标.md", "target")
        (self.vault / "asset.svg").write_text("image")
        self.note("folder/local.md", "[[目标]]")
        result = module.check_notes(str(self.vault), ["首页.md", "folder/local.md"])
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["files"], 2)

    def test_missing_target_is_reported_without_creation(self):
        self.note("首页.md", "[[missing]]")
        result = module.check_notes(str(self.vault), ["首页.md"])
        self.assertFalse(result["ok"])
        self.assertFalse((self.vault / "missing.md").exists())

    def test_table_alias_must_be_escaped(self):
        self.note("target.md", "original")
        self.note("bad.md", "| Name | Link |\n| A | [[target|label]] |")
        self.note("good.md", "| Name | Link |\n| A | [[target\\|label]] |")
        self.assertFalse(module.check_notes(str(self.vault), ["bad.md"])["ok"])
        result = module.check_notes(str(self.vault), ["good.md"])
        self.assertTrue(result["ok"], result)

    def test_fenced_and_inline_examples_are_not_links(self):
        self.note("首页.md", "```md\n[[example]]\n```\n~~~text\n[[other]]\n~~~\n`[[inline]]`")
        result = module.check_notes(str(self.vault), ["首页.md"])
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["results"][0]["links_checked"], 0)

    def test_explicit_scope_does_not_read_unselected_private_note(self):
        self.note("首页.md", "[[target]]")
        self.note("target.md", "[[unresolved-but-not-read]]")
        (self.vault / "private.md").write_bytes(b"\xff")
        result = module.check_notes(str(self.vault), ["首页.md"])
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["files"], 1)

    def test_outside_source_is_not_read(self):
        (self.root / "outside.md").write_text("private")
        result = module.check_notes(str(self.vault), ["../outside.md"])
        self.assertFalse(result["ok"])

    def test_outside_link_is_not_followed(self):
        self.note("首页.md", "[[../outside]]")
        (self.root / "outside.md").write_text("private")
        self.assertFalse(module.check_notes(str(self.vault), ["首页.md"])["ok"])

    def test_symlink_is_not_followed(self):
        outside = self.root / "outside.md"
        outside.write_text("private")
        (self.vault / "alias.md").symlink_to(outside)
        self.note("首页.md", "[[alias]]")
        self.assertFalse(module.check_notes(str(self.vault), ["首页.md"])["ok"])

    def test_missing_source_does_not_claim_success(self):
        self.assertFalse(module.check_notes(str(self.vault), ["missing.md"])["ok"])

    def test_existing_files_are_byte_identical_after_check(self):
        first = self.note("首页.md", "[[target]]\n")
        second = self.note("target.md", "original\n")
        before = {p: p.read_bytes() for p in (first, second)}
        module.check_notes(str(self.vault), ["首页.md"])
        self.assertEqual(before, {p: p.read_bytes() for p in (first, second)})


if __name__ == "__main__":
    unittest.main()
