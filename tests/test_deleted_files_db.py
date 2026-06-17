import os
import shutil
import tempfile
import unittest

from tools_library import path_db, deleted_files_db


class TestDeletedFilesDb(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig_paths_db = path_db.PATHS_DB_FILE
        self._orig_deleted_db = deleted_files_db.DELETED_FILES_DB_FILE
        path_db.PATHS_DB_FILE = os.path.join(self.tmp, "paths.db")
        deleted_files_db.DELETED_FILES_DB_FILE = os.path.join(self.tmp, "deleted_files.db")
        path_db.clear_cache()

    def tearDown(self):
        path_db.PATHS_DB_FILE = self._orig_paths_db
        deleted_files_db.DELETED_FILES_DB_FILE = self._orig_deleted_db
        path_db.clear_cache()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_record_and_get_recent(self):
        p1 = os.path.join(self.tmp, "a.txt")
        copy1 = os.path.join(self.tmp, "b.txt")
        deleted_files_db.record_deletion("hash1", p1, copy1, timestamp=1000.0)
        rows = deleted_files_db.get_recent_deletions()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["file_hash"], "hash1")
        self.assertEqual(os.path.normpath(rows[0]["path"]), os.path.normpath(p1))
        self.assertEqual(os.path.normpath(rows[0]["copy_path"]), os.path.normpath(copy1))

    def test_limit_and_newest_first_order(self):
        for i in range(15):
            deleted_files_db.record_deletion(
                f"h{i}", os.path.join(self.tmp, f"f{i}.txt"), None, timestamp=float(i))
        rows = deleted_files_db.get_recent_deletions(limit=10)
        self.assertEqual(len(rows), 10)
        self.assertEqual(rows[0]["file_hash"], "h14")
        self.assertEqual(rows[-1]["file_hash"], "h5")

    def test_no_copy_path_or_hash(self):
        p = os.path.join(self.tmp, "solo.txt")
        deleted_files_db.record_deletion(None, p, None)
        rows = deleted_files_db.get_recent_deletions()
        self.assertIsNone(rows[0]["copy_path"])
        self.assertIsNone(rows[0]["file_hash"])

    def test_no_paths_stored_as_raw_text(self):
        """The whole point of this DB: the raw path string must never appear verbatim
        in the underlying table — only as a resolved value via path_db."""
        import sqlite3
        p = os.path.join(self.tmp, "should_not_appear_raw.txt")
        deleted_files_db.record_deletion("h", p, None)
        conn = sqlite3.connect(deleted_files_db.DELETED_FILES_DB_FILE)
        try:
            row = conn.execute("SELECT path_id, copy_path_id FROM deleted_files").fetchone()
        finally:
            conn.close()
        self.assertIsInstance(row[0], int)


if __name__ == "__main__":
    unittest.main()
