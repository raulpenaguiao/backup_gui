import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from tools_library.pigmy_hash import compute_file_hash, save_pigmy_hash, load_pigmy_hash, index_vault


class TestComputeFileHash(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write(self, name, content):
        path = os.path.join(self.tmp, name)
        with open(path, "wb") as f:
            f.write(content)
        return path

    def test_deterministic(self):
        path = self._write("a.txt", b"hello world")
        self.assertEqual(compute_file_hash(path), compute_file_hash(path))

    def test_different_content_different_hash(self):
        p1 = self._write("a.txt", b"hello")
        p2 = self._write("b.txt", b"world")
        self.assertNotEqual(compute_file_hash(p1), compute_file_hash(p2))

    def test_same_content_same_hash(self):
        p1 = self._write("a.txt", b"identical")
        p2 = self._write("b.txt", b"identical")
        self.assertEqual(compute_file_hash(p1), compute_file_hash(p2))

    def test_missing_file_returns_none(self):
        self.assertIsNone(compute_file_hash("/nonexistent/ghost.txt"))

    def test_returns_string(self):
        path = self._write("c.txt", b"data")
        result = compute_file_hash(path)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


class TestPigmyHashRoundtrip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_save_and_load(self):
        original = {
            "abc123": [["/a/b.txt", "/c/d.txt"]],
            "def456": [["/e/f.txt"]],
        }
        save_pigmy_hash(self.tmp, original)
        loaded, indexed_at = load_pigmy_hash(self.tmp)
        # load_pigmy_hash normalizes separators, so compare against normpath'd expected
        expected = {
            h: [[os.path.normpath(p) for p in group] for group in groups]
            for h, groups in original.items()
        }
        self.assertEqual(expected, loaded)
        self.assertIsNotNone(indexed_at)
        self.assertIsInstance(indexed_at, float)

    def test_empty_hash_roundtrip(self):
        save_pigmy_hash(self.tmp, {})
        loaded, indexed_at = load_pigmy_hash(self.tmp)
        self.assertEqual(loaded, {})
        self.assertIsNotNone(indexed_at)


class TestIndexVaultSkipped(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write(self, rel, content=b"data"):
        path = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)
        return path

    def test_returns_tuple(self):
        self._write("a.txt", b"hello")
        result = index_vault(self.tmp)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_normal_files_indexed(self):
        self._write("a.txt", b"hello")
        self._write("b.txt", b"world")
        pigmyhash, skipped = index_vault(self.tmp)
        self.assertIsNotNone(pigmyhash)
        self.assertEqual(skipped, [])
        all_paths = [p for groups in pigmyhash.values() for g in groups for p in g]
        self.assertTrue(any("a.txt" in p for p in all_paths))

    @unittest.skipIf(
        not hasattr(os, "getuid") or os.getuid() == 0,
        "Windows or root — chmod permission test not applicable",
    )
    def test_unreadable_file_triggers_real_os_error(self):
        """Remove read permission on a file and confirm index_vault skips it."""
        self._write("ok.txt", b"readable")
        locked = self._write("locked.txt", b"cannot read this")
        os.chmod(locked, 0o000)
        try:
            pigmyhash, skipped = index_vault(self.tmp)
        finally:
            os.chmod(locked, 0o644)  # restore so tearDown can delete it

        skipped_paths = [p for p, _ in skipped]
        self.assertTrue(any("locked" in p for p in skipped_paths),
                        f"Expected locked.txt in skipped, got: {skipped_paths}")
        # The readable file must still be indexed
        all_paths = [p for groups in pigmyhash.values()
                     for g in groups for p in g]
        self.assertTrue(any("ok" in p for p in all_paths),
                        "Readable file should still appear in pigmyhash")

    @unittest.skipUnless(sys.platform == "win32", "Windows icacls permission test")
    def test_unreadable_file_triggers_real_os_error_windows(self):
        """Deny read access via icacls (Windows ACL) and confirm index_vault skips the file."""
        self._write("ok.txt", b"readable")
        locked = self._write("locked_win.txt", b"cannot read this")
        username = os.environ.get("USERNAME", "")
        subprocess.run(
            ["icacls", locked, "/deny", f"{username}:(R)"],
            check=True, capture_output=True,
        )
        try:
            pigmyhash, skipped = index_vault(self.tmp)
        finally:
            subprocess.run(
                ["icacls", locked, "/remove:d", username],
                check=True, capture_output=True,
            )
        skipped_paths = [p for p, _ in skipped]
        self.assertTrue(
            any("locked_win" in p for p in skipped_paths),
            f"Expected locked_win.txt in skipped, got: {skipped_paths}",
        )
        all_paths = [p for groups in pigmyhash.values() for g in groups for p in g]
        self.assertTrue(any("ok" in p for p in all_paths),
                        "Readable file should still appear in pigmyhash")

    def test_unreadable_file_appears_in_skipped_via_mock(self):
        from unittest import mock
        import tools_library.pigmy_hash as ph
        self._write("ok.txt", b"readable")
        self._write("locked.txt", b"locked")

        original_hash_file = ph._hash_file

        def fake_hash(path):
            if "locked" in path:
                return None, "The file cannot be accessed by the system"
            return original_hash_file(path)

        with mock.patch("tools_library.pigmy_hash._hash_file", side_effect=fake_hash):
            pigmyhash, skipped = index_vault(self.tmp)

        self.assertTrue(any("locked" in p for p, _ in skipped))
        self.assertTrue(any("cannot be accessed" in e for _, e in skipped))

    def test_cancelled_returns_none_pigmyhash(self):
        import threading
        self._write("a.txt", b"data")
        cancel = threading.Event()
        cancel.set()
        pigmyhash, skipped = index_vault(self.tmp, cancel_token=cancel)
        self.assertIsNone(pigmyhash)


if __name__ == "__main__":
    unittest.main()
