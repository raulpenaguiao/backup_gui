import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

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


class TestPigmyHashCache(unittest.TestCase):
    """Covers the SQLite-backed incremental cache (.pigmy-hash-db): unchanged
    files are never re-hashed, changed/deleted files are detected correctly,
    and load_pigmy_hash's pure-DB reconstruction matches a live index_vault."""

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

    def test_empty_vault_roundtrip(self):
        pigmyhash, skipped = index_vault(self.tmp)
        self.assertEqual(pigmyhash, {})
        indexed_at = save_pigmy_hash(self.tmp, pigmyhash)
        self.assertIsInstance(indexed_at, float)
        loaded, loaded_at = load_pigmy_hash(self.tmp)
        self.assertEqual(loaded, {})
        self.assertEqual(loaded_at, indexed_at)

    def test_second_index_run_does_not_rehash_unchanged_files(self):
        self._write("a.txt", b"hello")
        self._write("sub/b.txt", b"world")
        index_vault(self.tmp)

        calls = []
        import tools_library.pigmy_hash as ph
        original = ph._hash_file

        def counting(path):
            calls.append(path)
            return original(path)

        with mock.patch("tools_library.pigmy_hash._hash_file", side_effect=counting):
            index_vault(self.tmp)
        self.assertEqual(calls, [], f"expected no rehashing, but got: {calls}")

    def test_modified_file_triggers_rehash_only_for_that_file(self):
        a = self._write("a.txt", b"hello")
        self._write("b.txt", b"world")
        index_vault(self.tmp)

        time.sleep(0.01)
        with open(a, "wb") as f:
            f.write(b"hello, but different now")
        os.utime(a, None)

        import tools_library.pigmy_hash as ph
        calls = []
        original = ph._hash_file

        def counting(path):
            calls.append(path)
            return original(path)

        with mock.patch("tools_library.pigmy_hash._hash_file", side_effect=counting):
            pigmyhash, skipped = index_vault(self.tmp)
        self.assertEqual(calls, [a])
        all_paths = [p for g in pigmyhash.values() for grp in g for p in grp]
        self.assertTrue(any("a.txt" in p for p in all_paths))

    def test_deleted_file_pruned_from_result_and_cache(self):
        a = self._write("a.txt", b"hello")
        b = self._write("b.txt", b"world")
        index_vault(self.tmp)

        os.remove(b)
        pigmyhash, skipped = index_vault(self.tmp)
        all_paths = [p for g in pigmyhash.values() for grp in g for p in grp]
        self.assertFalse(any("b.txt" in p for p in all_paths))
        self.assertTrue(any("a.txt" in p for p in all_paths))

        # Confirm it's gone from the cache itself, not just this run's result.
        save_pigmy_hash(self.tmp, pigmyhash)
        loaded, _ = load_pigmy_hash(self.tmp)
        loaded_paths = [p for g in loaded.values() for grp in g for p in grp]
        self.assertFalse(any("b.txt" in p for p in loaded_paths))

    def test_load_pigmy_hash_matches_live_index_including_folder_hashes(self):
        self._write("a.txt", b"hello")
        self._write("sub/b.txt", b"world")
        self._write("sub/deeper/c.txt", b"hello")  # same content as a.txt
        pigmyhash, _ = index_vault(self.tmp)
        save_pigmy_hash(self.tmp, pigmyhash)
        loaded, _ = load_pigmy_hash(self.tmp)
        self.assertEqual(loaded, pigmyhash)

        # Folder-level hashes must be present too (not just files).
        all_paths = [p for g in loaded.values() for grp in g for p in grp]
        self.assertTrue(any(p.endswith("sub") for p in all_paths))

    def test_save_pigmy_hash_returns_increasing_timestamps(self):
        self._write("a.txt", b"hello")
        pigmyhash, _ = index_vault(self.tmp)
        t1 = save_pigmy_hash(self.tmp, pigmyhash)
        time.sleep(0.01)
        t2 = save_pigmy_hash(self.tmp, pigmyhash)
        self.assertGreater(t2, t1)


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
        # Deny only the granular "read data" right (RD), not the simple "(R)" permission —
        # (R) also denies READ_CONTROL, which can strip our own ability to ever modify this
        # ACL again (a self-lockout requiring takeown/icacls /reset to recover from).
        subprocess.run(
            ["icacls", locked, "/deny", f"{username}:(RD)"],
            check=True, capture_output=True,
        )
        try:
            pigmyhash, skipped = index_vault(self.tmp)
        finally:
            # Best-effort cleanup — must not raise, or it would mask a real assertion
            # failure above and leave the temp dir's rmtree (in tearDown) to deal with
            # a still-locked file.
            subprocess.run(
                ["icacls", locked, "/remove:d", username],
                capture_output=True,
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
