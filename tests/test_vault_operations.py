import os
import shutil
import tempfile
import threading
import unittest
from unittest import mock

from tools_library.vault_operations import (
    get_repetitions, is_external_inside_vault, filter_external_vault,
)
from tools_library.pigmy_hash import compute_file_hash


class TestGetRepetitions(unittest.TestCase):
    def test_no_repetitions(self):
        pigmyhash = {"h1": [["/a/b.txt"]], "h2": [["/c/d.txt"]]}
        self.assertEqual(get_repetitions(pigmyhash), [])

    def test_empty_hash(self):
        self.assertEqual(get_repetitions({}), [])

    def test_with_real_duplicate_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            f1 = os.path.join(tmp, "a.txt")
            f2 = os.path.join(tmp, "b.txt")
            open(f1, "w").close()
            open(f2, "w").close()
            pigmyhash = {"h1": [[f1, f2]]}
            reps = get_repetitions(pigmyhash)
            self.assertEqual(len(reps), 1)
            self.assertIn(f1, reps[0])
            self.assertIn(f2, reps[0])

    def test_group_with_one_existing_file_not_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            f1 = os.path.join(tmp, "a.txt")
            open(f1, "w").close()
            # second path does not exist
            pigmyhash = {"h1": [[f1, "/nonexistent/b.txt"]]}
            reps = get_repetitions(pigmyhash)
            self.assertEqual(reps, [])

    def test_multiple_groups(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = [os.path.join(tmp, f"{i}.txt") for i in range(4)]
            for f in files:
                open(f, "w").close()
            pigmyhash = {
                "h1": [[files[0], files[1]]],
                "h2": [[files[2], files[3]]],
            }
            reps = get_repetitions(pigmyhash)
            self.assertEqual(len(reps), 2)


class TestIsExternalInsideVault(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.vault = os.path.join(self.tmp, "vault")
        os.makedirs(self.vault)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_equal_paths_rejected(self):
        self.assertTrue(is_external_inside_vault(self.vault, self.vault))

    def test_subdir_rejected(self):
        subdir = os.path.join(self.vault, "sub")
        self.assertTrue(is_external_inside_vault(self.vault, subdir))

    def test_deep_subdir_rejected(self):
        deep = os.path.join(self.vault, "a", "b", "c")
        self.assertTrue(is_external_inside_vault(self.vault, deep))

    def test_sibling_accepted(self):
        sibling = os.path.join(self.tmp, "other")
        self.assertFalse(is_external_inside_vault(self.vault, sibling))

    def test_parent_accepted(self):
        self.assertFalse(is_external_inside_vault(self.vault, self.tmp))

    def test_unrelated_path_accepted(self):
        self.assertFalse(is_external_inside_vault(self.vault, "/completely/different"))

    def test_name_prefix_not_confused(self):
        # "/vault_backup" must not match "/vault"
        vault_backup = self.vault + "_backup"
        self.assertFalse(is_external_inside_vault(self.vault, vault_backup))


class TestFilterExternalVault(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.vault = os.path.join(self.tmp, "vault")
        self.ext = os.path.join(self.tmp, "external")
        os.makedirs(self.vault)
        os.makedirs(self.ext)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write(self, base, relpath, content):
        full = os.path.join(base, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(content)
        return full

    def test_no_match_returns_empty(self):
        self._write(self.ext, "file.txt", b"unique content")
        with mock.patch("tools_library.vault_operations.send2trash.send2trash") as m:
            result = filter_external_vault({}, self.ext)
        m.assert_not_called()
        self.assertEqual(result, [])

    def test_matching_file_reported_and_trashed(self):
        vault_f = self._write(self.vault, "doc.txt", b"same content")
        ext_f = self._write(self.ext, "doc.txt", b"same content")
        h = compute_file_hash(vault_f)
        pigmyhash = {h: [[vault_f]]}
        with mock.patch("tools_library.vault_operations.send2trash.send2trash") as m:
            result = filter_external_vault(pigmyhash, self.ext)
        self.assertEqual(len(result), 1)
        self.assertEqual(os.path.normpath(result[0]), os.path.normpath(ext_f))
        m.assert_called_once()

    def test_different_content_not_deleted(self):
        vault_f = self._write(self.vault, "doc.txt", b"vault content")
        self._write(self.ext, "doc.txt", b"different content")
        h = compute_file_hash(vault_f)
        pigmyhash = {h: [[vault_f]]}
        with mock.patch("tools_library.vault_operations.send2trash.send2trash") as m:
            result = filter_external_vault(pigmyhash, self.ext)
        m.assert_not_called()
        self.assertEqual(result, [])

    def test_stop_event_cancels_before_processing(self):
        for i in range(3):
            self._write(self.ext, f"f{i}.txt", f"content {i}".encode())
        stop = threading.Event()
        stop.set()
        with mock.patch("tools_library.vault_operations.send2trash.send2trash") as m:
            result = filter_external_vault({}, self.ext, stop_event=stop)
        m.assert_not_called()
        self.assertEqual(result, [])

    def test_progress_callback_called(self):
        self._write(self.ext, "a.txt", b"data")
        calls = []
        with mock.patch("tools_library.vault_operations.send2trash.send2trash"):
            filter_external_vault({}, self.ext, progress_callback=lambda c, t: calls.append((c, t)))
        self.assertGreater(len(calls), 0)
        # Last call should be (total, total)
        last = calls[-1]
        self.assertEqual(last[0], last[1])

    def test_empty_external_dir(self):
        with mock.patch("tools_library.vault_operations.send2trash.send2trash") as m:
            result = filter_external_vault({}, self.ext)
        m.assert_not_called()
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
