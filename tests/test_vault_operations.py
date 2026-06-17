import os
import shutil
import tempfile
import threading
import unittest
from unittest import mock

from tools_library.vault_operations import (
    get_repetitions, paths_overlap, filter_external_vault,
    scan_external_vault, find_copies_in_external, find_internal_duplicates,
    delete_marked_files,
)
from tools_library.pigmy_hash import compute_file_hash, index_vault, save_pigmy_hash
from tools_library import path_db, deleted_files_db


class TestGetRepetitions(unittest.TestCase):
    def test_no_repetitions(self):
        pigmyhash = {"h1": [["/a/b.txt"]], "h2": [["/c/d.txt"]]}
        reps, stale = get_repetitions(pigmyhash)
        self.assertEqual(reps, [])
        self.assertEqual(stale, 0)

    def test_empty_hash(self):
        reps, stale = get_repetitions({})
        self.assertEqual(reps, [])
        self.assertEqual(stale, 0)

    def test_with_real_duplicate_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            f1 = os.path.join(tmp, "a.txt")
            f2 = os.path.join(tmp, "b.txt")
            open(f1, "w").close()
            open(f2, "w").close()
            pigmyhash = {"h1": [[f1, f2]]}
            reps, stale = get_repetitions(pigmyhash)
            self.assertEqual(len(reps), 1)
            self.assertIn(f1, reps[0])
            self.assertIn(f2, reps[0])
            self.assertEqual(stale, 0)

    def test_group_with_one_existing_file_not_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            f1 = os.path.join(tmp, "a.txt")
            open(f1, "w").close()
            # second path does not exist
            pigmyhash = {"h1": [[f1, "/nonexistent/b.txt"]]}
            reps, stale = get_repetitions(pigmyhash)
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
            reps, stale = get_repetitions(pigmyhash)
            self.assertEqual(len(reps), 2)

    def test_stale_file_excluded(self):
        import time
        with tempfile.TemporaryDirectory() as tmp:
            f1 = os.path.join(tmp, "a.txt")
            f2 = os.path.join(tmp, "b.txt")
            open(f1, "w").close()
            open(f2, "w").close()
            # indexed_at in the past so both files appear stale
            indexed_at = os.path.getmtime(f1) - 1
            pigmyhash = {"h1": [[f1, f2]]}
            reps, stale = get_repetitions(pigmyhash, indexed_at=indexed_at)
            self.assertEqual(reps, [])
            self.assertEqual(stale, 2)

    def test_fresh_index_shows_no_stale(self):
        import time
        with tempfile.TemporaryDirectory() as tmp:
            f1 = os.path.join(tmp, "a.txt")
            f2 = os.path.join(tmp, "b.txt")
            open(f1, "w").close()
            open(f2, "w").close()
            # indexed_at in the future so both files appear current
            indexed_at = time.time() + 60
            pigmyhash = {"h1": [[f1, f2]]}
            reps, stale = get_repetitions(pigmyhash, indexed_at=indexed_at)
            self.assertEqual(len(reps), 1)
            self.assertEqual(stale, 0)


class TestPathsOverlap(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.vault = os.path.join(self.tmp, "vault")
        os.makedirs(self.vault)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_equal_paths_rejected(self):
        self.assertTrue(paths_overlap(self.vault, self.vault))

    def test_ev_inside_vault_rejected(self):
        subdir = os.path.join(self.vault, "sub")
        self.assertTrue(paths_overlap(self.vault, subdir))

    def test_ev_deep_inside_vault_rejected(self):
        deep = os.path.join(self.vault, "a", "b", "c")
        self.assertTrue(paths_overlap(self.vault, deep))

    def test_vault_inside_ev_rejected(self):
        # EV is a parent of the vault — vault would be scanned and deleted
        self.assertTrue(paths_overlap(self.vault, self.tmp))

    def test_vault_deep_inside_ev_rejected(self):
        grandparent = os.path.dirname(self.tmp)
        self.assertTrue(paths_overlap(self.vault, grandparent))

    def test_sibling_accepted(self):
        sibling = os.path.join(self.tmp, "other")
        self.assertFalse(paths_overlap(self.vault, sibling))

    def test_unrelated_path_accepted(self):
        self.assertFalse(paths_overlap(self.vault, "/completely/different"))

    def test_name_prefix_not_confused(self):
        # "/vault_backup" must not match "/vault"
        vault_backup = self.vault + "_backup"
        self.assertFalse(paths_overlap(self.vault, vault_backup))


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


class TestScanExternalVault(unittest.TestCase):
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

    def test_returns_empty_when_no_match(self):
        self._write(self.ext, "a.txt", b"unique")
        all_files, matched = scan_external_vault({}, self.ext)
        self.assertEqual(len(all_files), 1)
        self.assertEqual(matched, [])

    def test_returns_match_without_deleting(self):
        vault_f = self._write(self.vault, "doc.txt", b"same content")
        ext_f = self._write(self.ext, "doc.txt", b"same content")
        h = compute_file_hash(vault_f)
        pigmyhash = {h: [[vault_f]]}
        all_files, matched = scan_external_vault(pigmyhash, self.ext)
        self.assertIn(ext_f, matched)
        self.assertTrue(os.path.exists(ext_f), "scan must not delete files")

    def test_different_content_not_matched(self):
        vault_f = self._write(self.vault, "doc.txt", b"vault content")
        self._write(self.ext, "doc.txt", b"different content")
        h = compute_file_hash(vault_f)
        pigmyhash = {h: [[vault_f]]}
        _, matched = scan_external_vault(pigmyhash, self.ext)
        self.assertEqual(matched, [])

    def test_stop_event_halts_scan(self):
        for i in range(5):
            self._write(self.ext, f"f{i}.txt", f"content {i}".encode())
        stop = threading.Event()
        stop.set()
        all_files, matched = scan_external_vault({}, self.ext, stop_event=stop)
        self.assertEqual(matched, [])

    def test_match_callback_called(self):
        vault_f = self._write(self.vault, "cb.txt", b"callback content")
        self._write(self.ext, "cb.txt", b"callback content")
        h = compute_file_hash(vault_f)
        pigmyhash = {h: [[vault_f]]}
        cb_calls = []
        scan_external_vault(pigmyhash, self.ext, match_callback=lambda p: cb_calls.append(p))
        self.assertEqual(len(cb_calls), 1)

    def test_progress_callback_called(self):
        self._write(self.ext, "p.txt", b"progress test")
        calls = []
        scan_external_vault({}, self.ext, progress_callback=lambda c, t: calls.append((c, t)))
        self.assertGreater(len(calls), 0)
        self.assertEqual(calls[-1][0], calls[-1][1])

    def test_all_files_list_complete(self):
        for i in range(4):
            self._write(self.ext, f"f{i}.txt", b"data")
        all_files, _ = scan_external_vault({}, self.ext)
        self.assertEqual(len(all_files), 4)


class _DbIsolatedTestCase(unittest.TestCase):
    """Redirects path_db/deleted_files_db to a temp file so tests never touch the real log/ dbs."""

    def setUp(self):
        self.db_tmp = tempfile.mkdtemp()
        self._orig_paths_db = path_db.PATHS_DB_FILE
        self._orig_deleted_db = deleted_files_db.DELETED_FILES_DB_FILE
        path_db.PATHS_DB_FILE = os.path.join(self.db_tmp, "paths.db")
        deleted_files_db.DELETED_FILES_DB_FILE = os.path.join(self.db_tmp, "deleted_files.db")
        path_db.clear_cache()

    def tearDown(self):
        path_db.PATHS_DB_FILE = self._orig_paths_db
        deleted_files_db.DELETED_FILES_DB_FILE = self._orig_deleted_db
        path_db.clear_cache()
        shutil.rmtree(self.db_tmp, ignore_errors=True)


class TestFindCopiesInExternal(_DbIsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp()
        self.vault = os.path.join(self.tmp, "vault")
        self.ext = os.path.join(self.tmp, "external")
        os.makedirs(self.vault)
        os.makedirs(self.ext)

    def tearDown(self):
        shutil.rmtree(self.tmp)
        super().tearDown()

    def _write(self, base, relpath, content):
        full = os.path.join(base, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(content)
        return full

    def test_finds_copy_without_rehashing_ev(self):
        vault_f = self._write(self.vault, "doc.txt", b"same content")
        ev_f = self._write(self.ext, "doc.txt", b"same content")
        main_hash, _ = index_vault(self.vault)
        ev_hash, _ = index_vault(self.ext)
        matches = []
        find_copies_in_external(main_hash, ev_hash,
                                match_callback=lambda *args: matches.append(args))
        self.assertEqual(len(matches), 1)
        path, size, file_hash, copy_path = matches[0]
        self.assertEqual(os.path.normpath(path), os.path.normpath(ev_f))
        self.assertEqual(os.path.normpath(copy_path), os.path.normpath(vault_f))

    def test_no_match_when_content_differs(self):
        self._write(self.vault, "doc.txt", b"vault content")
        self._write(self.ext, "doc.txt", b"different content")
        main_hash, _ = index_vault(self.vault)
        ev_hash, _ = index_vault(self.ext)
        matches = []
        find_copies_in_external(main_hash, ev_hash,
                                match_callback=lambda *args: matches.append(args))
        self.assertEqual(matches, [])

    def test_stop_event_halts(self):
        self._write(self.vault, "doc.txt", b"same content")
        self._write(self.ext, "doc.txt", b"same content")
        main_hash, _ = index_vault(self.vault)
        ev_hash, _ = index_vault(self.ext)
        stop = threading.Event()
        stop.set()
        matches = []
        find_copies_in_external(main_hash, ev_hash, stop_event=stop,
                                match_callback=lambda *args: matches.append(args))
        self.assertEqual(matches, [])


class TestFindInternalDuplicates(_DbIsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp()
        self.ext = os.path.join(self.tmp, "external")
        os.makedirs(self.ext)

    def tearDown(self):
        shutil.rmtree(self.tmp)
        super().tearDown()

    def _write(self, relpath, content):
        full = os.path.join(self.ext, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(content)
        return full

    def test_pair_keeps_first_deletes_last(self):
        a = self._write("a.txt", b"dup")
        b = self._write("b.txt", b"dup")
        ev_hash, _ = index_vault(self.ext)
        matches = []
        find_internal_duplicates(ev_hash, match_callback=lambda *args: matches.append(args))
        self.assertEqual(len(matches), 1)
        path, size, file_hash, copy_path = matches[0]
        expected_keep, expected_delete = sorted([a, b])
        self.assertEqual(os.path.normpath(path), os.path.normpath(expected_delete))
        self.assertEqual(os.path.normpath(copy_path), os.path.normpath(expected_keep))

    def test_group_of_three_keeps_first_deletes_rest(self):
        paths = sorted([self._write(f"{n}.txt", b"triple") for n in ("c", "a", "b")])
        ev_hash, _ = index_vault(self.ext)
        matches = []
        find_internal_duplicates(ev_hash, match_callback=lambda *args: matches.append(args))
        deleted = sorted(os.path.normpath(m[0]) for m in matches)
        self.assertEqual(deleted, [os.path.normpath(p) for p in paths[1:]])
        for m in matches:
            self.assertEqual(os.path.normpath(m[3]), os.path.normpath(paths[0]))

    def test_no_duplicates_no_matches(self):
        self._write("a.txt", b"one")
        self._write("b.txt", b"two")
        ev_hash, _ = index_vault(self.ext)
        matches = []
        find_internal_duplicates(ev_hash, match_callback=lambda *args: matches.append(args))
        self.assertEqual(matches, [])


class TestDeleteMarkedFiles(_DbIsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)
        super().tearDown()

    def _write(self, relpath, content=b"x"):
        full = os.path.join(self.tmp, relpath)
        with open(full, "wb") as f:
            f.write(content)
        return full

    def test_trash_deletion_records_to_db(self):
        f = self._write("a.txt")
        keeper = self._write("keep.txt")
        suggestions = [{"path": f, "hash": "h1", "copy_path": keeper}]
        with mock.patch("tools_library.vault_operations.send2trash.send2trash") as m:
            deleted, errors = delete_marked_files(suggestions, use_trash=True)
        m.assert_called_once()
        self.assertEqual(deleted, [f])
        self.assertEqual(errors, [])
        rows = deleted_files_db.get_recent_deletions()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["file_hash"], "h1")

    def test_permanent_deletion_uses_os_remove(self):
        f = self._write("b.txt")
        suggestions = [{"path": f, "hash": "h2", "copy_path": None}]
        with mock.patch("tools_library.vault_operations.send2trash.send2trash") as trash_mock:
            deleted, errors = delete_marked_files(suggestions, use_trash=False)
        trash_mock.assert_not_called()
        self.assertFalse(os.path.exists(f))
        self.assertEqual(deleted, [f])

    def test_error_is_collected_not_raised(self):
        suggestions = [{"path": os.path.join(self.tmp, "missing.txt"), "hash": None, "copy_path": None}]
        deleted, errors = delete_marked_files(suggestions, use_trash=False)
        self.assertEqual(deleted, [])
        self.assertEqual(len(errors), 1)

    def test_stop_event_halts_before_processing(self):
        f = self._write("c.txt")
        suggestions = [{"path": f, "hash": None, "copy_path": None}]
        stop = threading.Event()
        stop.set()
        with mock.patch("tools_library.vault_operations.send2trash.send2trash") as m:
            deleted, errors = delete_marked_files(suggestions, use_trash=True, stop_event=stop)
        m.assert_not_called()
        self.assertEqual(deleted, [])


if __name__ == "__main__":
    unittest.main()
