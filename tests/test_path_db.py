import os
import shutil
import sqlite3
import tempfile
import unittest

from tools_library import path_db


class TestPathDb(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig_db_file = path_db.PATHS_DB_FILE
        path_db.PATHS_DB_FILE = os.path.join(self.tmp, "paths.db")
        path_db.clear_cache()

    def tearDown(self):
        path_db.PATHS_DB_FILE = self._orig_db_file
        path_db.clear_cache()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_round_trip(self):
        p = os.path.join(self.tmp, "a", "b", "c.txt")
        pid = path_db.get_path_id(p)
        self.assertIsInstance(pid, int)
        self.assertEqual(os.path.normpath(path_db.resolve_path(pid)), os.path.normpath(p))

    def test_same_path_returns_same_id(self):
        p = os.path.join(self.tmp, "x", "y.txt")
        id1 = path_db.get_path_id(p)
        id2 = path_db.get_path_id(p)
        self.assertEqual(id1, id2)

    def test_shared_prefix_reuses_parent_row(self):
        base = os.path.join(self.tmp, "shared")
        p1 = os.path.join(base, "one.txt")
        p2 = os.path.join(base, "two.txt")
        path_db.get_path_id(p1)
        path_db.get_path_id(p2)

        conn = sqlite3.connect(path_db.PATHS_DB_FILE)
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM paths WHERE name = ?", (os.path.basename(base),)
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(count, 1)

    def test_unrelated_paths_get_different_ids(self):
        id1 = path_db.get_path_id(os.path.join(self.tmp, "one.txt"))
        id2 = path_db.get_path_id(os.path.join(self.tmp, "two.txt"))
        self.assertNotEqual(id1, id2)

    def test_resolve_unknown_id_returns_none(self):
        self.assertIsNone(path_db.resolve_path(999999))

    def test_resolve_none_returns_none(self):
        self.assertIsNone(path_db.resolve_path(None))


if __name__ == "__main__":
    unittest.main()
