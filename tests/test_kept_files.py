import os
import shutil
import tempfile
import unittest

from tools_library.kept_files import load_kept, save_kept, add_kept, remove_kept, is_kept


class TestLoadKept(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_nonexistent_returns_empty_set(self):
        self.assertEqual(load_kept(self.tmp), set())

    def test_roundtrip(self):
        original = {("hash1", "notes/file.txt"), ("hash2", "folder/doc.pdf")}
        save_kept(self.tmp, original)
        self.assertEqual(load_kept(self.tmp), original)

    def test_empty_set_roundtrip(self):
        save_kept(self.tmp, set())
        self.assertEqual(load_kept(self.tmp), set())


class TestAddKept(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.file = os.path.join(self.tmp, "file.txt")
        open(self.file, "w").close()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_adds_entry(self):
        result = add_kept(self.tmp, self.file, "abc123")
        rel = os.path.relpath(os.path.normpath(self.file), os.path.normpath(self.tmp))
        self.assertIn(("abc123", rel), result)

    def test_persists_to_disk(self):
        add_kept(self.tmp, self.file, "abc123")
        loaded = load_kept(self.tmp)
        rel = os.path.relpath(os.path.normpath(self.file), os.path.normpath(self.tmp))
        self.assertIn(("abc123", rel), loaded)

    def test_idempotent(self):
        add_kept(self.tmp, self.file, "abc123")
        add_kept(self.tmp, self.file, "abc123")
        loaded = load_kept(self.tmp)
        rel = os.path.relpath(os.path.normpath(self.file), os.path.normpath(self.tmp))
        count = sum(1 for e in loaded if e == ("abc123", rel))
        self.assertEqual(count, 1)

    def test_nested_path(self):
        subdir = os.path.join(self.tmp, "notes", "2024")
        os.makedirs(subdir)
        nested = os.path.join(subdir, "report.pdf")
        open(nested, "w").close()
        add_kept(self.tmp, nested, "def456")
        loaded = load_kept(self.tmp)
        rel = os.path.relpath(os.path.normpath(nested), os.path.normpath(self.tmp))
        self.assertIn(("def456", rel), loaded)


class TestRemoveKept(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.file = os.path.join(self.tmp, "file.txt")
        open(self.file, "w").close()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_removes_entry(self):
        add_kept(self.tmp, self.file, "abc123")
        rel = os.path.relpath(os.path.normpath(self.file), os.path.normpath(self.tmp))
        remove_kept(self.tmp, "abc123", rel)
        self.assertNotIn(("abc123", rel), load_kept(self.tmp))

    def test_remove_nonexistent_is_safe(self):
        remove_kept(self.tmp, "ghost", "nonexistent.txt")

    def test_other_entries_preserved(self):
        f2 = os.path.join(self.tmp, "other.txt")
        open(f2, "w").close()
        add_kept(self.tmp, self.file, "abc123")
        add_kept(self.tmp, f2, "def456")
        rel1 = os.path.relpath(os.path.normpath(self.file), os.path.normpath(self.tmp))
        remove_kept(self.tmp, "abc123", rel1)
        loaded = load_kept(self.tmp)
        self.assertNotIn(("abc123", rel1), loaded)
        rel2 = os.path.relpath(os.path.normpath(f2), os.path.normpath(self.tmp))
        self.assertIn(("def456", rel2), loaded)


class TestIsKept(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.file = os.path.join(self.tmp, "file.txt")
        open(self.file, "w").close()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_true_after_add(self):
        add_kept(self.tmp, self.file, "abc123")
        self.assertTrue(is_kept(self.tmp, self.file, "abc123"))

    def test_false_wrong_hash(self):
        add_kept(self.tmp, self.file, "abc123")
        self.assertFalse(is_kept(self.tmp, self.file, "wronghash"))

    def test_false_unknown_file(self):
        self.assertFalse(is_kept(self.tmp, self.file, "abc123"))

    def test_false_after_remove(self):
        add_kept(self.tmp, self.file, "abc123")
        rel = os.path.relpath(os.path.normpath(self.file), os.path.normpath(self.tmp))
        remove_kept(self.tmp, "abc123", rel)
        self.assertFalse(is_kept(self.tmp, self.file, "abc123"))


if __name__ == "__main__":
    unittest.main()
