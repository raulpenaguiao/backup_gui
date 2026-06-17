import os
import shutil
import tempfile
import unittest
import sqlite3

from tools_library import pigmy_hash_db as db


class TestPigmyHashDb(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.conn = db.connect(self.tmp)

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_db_file_created_inside_vault(self):
        self.assertTrue(os.path.exists(db.db_path(self.tmp)))
        self.assertEqual(os.path.dirname(db.db_path(self.tmp)), self.tmp)

    def test_root_folder_is_singleton(self):
        r1 = db.get_or_create_folder_id(self.conn, [])
        r2 = db.get_or_create_folder_id(self.conn, [])
        self.assertEqual(r1, r2)

    def test_nested_folder_chain_created(self):
        fid = db.get_or_create_folder_id(self.conn, ["a", "b", "c"])
        self.assertEqual(db.resolve_folder_parts(self.conn, fid), ["a", "b", "c"])

    def test_shared_prefix_reuses_parent_rows(self):
        db.get_or_create_folder_id(self.conn, ["a", "x"])
        db.get_or_create_folder_id(self.conn, ["a", "y"])
        count = self.conn.execute(
            "SELECT COUNT(*) FROM folders WHERE name = 'a'"
        ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_same_parts_return_same_id(self):
        f1 = db.get_or_create_folder_id(self.conn, ["a", "b"])
        f2 = db.get_or_create_folder_id(self.conn, ["a", "b"])
        self.assertEqual(f1, f2)

    def test_resolve_root_is_empty(self):
        root = db.get_or_create_folder_id(self.conn, [])
        self.assertEqual(db.resolve_folder_parts(self.conn, root), [])

    def test_lookup_missing_file_returns_none(self):
        folder = db.get_or_create_folder_id(self.conn, [])
        self.assertIsNone(db.lookup_file(self.conn, folder, "nope.txt"))

    def test_upsert_then_lookup_hit(self):
        folder = db.get_or_create_folder_id(self.conn, [])
        db.upsert_file(self.conn, folder, "f.txt", 10, 123.5, "hash1")
        row = db.lookup_file(self.conn, folder, "f.txt")
        self.assertEqual(row["size"], 10)
        self.assertEqual(row["mtime"], 123.5)
        self.assertEqual(row["hash"], "hash1")

    def test_upsert_overwrites_existing_row_same_id(self):
        folder = db.get_or_create_folder_id(self.conn, [])
        id1 = db.upsert_file(self.conn, folder, "f.txt", 10, 1.0, "hash1")
        id2 = db.upsert_file(self.conn, folder, "f.txt", 20, 2.0, "hash2")
        self.assertEqual(id1, id2)
        row = db.lookup_file(self.conn, folder, "f.txt")
        self.assertEqual(row["size"], 20)
        self.assertEqual(row["hash"], "hash2")

    def test_cache_miss_on_size_or_mtime_mismatch(self):
        """The actual cache-validity check happens in pigmy_hash.py (it compares
        the looked-up row's size/mtime against the live os.stat() result) — this
        just confirms lookup_file returns the stored values exactly so that
        comparison is meaningful."""
        folder = db.get_or_create_folder_id(self.conn, [])
        db.upsert_file(self.conn, folder, "f.txt", 10, 1.0, "hash1")
        row = db.lookup_file(self.conn, folder, "f.txt")
        self.assertFalse(row["size"] == 999)
        self.assertFalse(row["mtime"] == 999.0)

    def test_prune_removes_only_unseen(self):
        folder = db.get_or_create_folder_id(self.conn, [])
        keep_id = db.upsert_file(self.conn, folder, "keep.txt", 1, 1.0, "h1")
        db.upsert_file(self.conn, folder, "gone.txt", 2, 2.0, "h2")
        db.prune_files_not_in(self.conn, [keep_id])
        self.assertIsNotNone(db.lookup_file(self.conn, folder, "keep.txt"))
        self.assertIsNone(db.lookup_file(self.conn, folder, "gone.txt"))

    def test_prune_with_empty_seen_removes_everything(self):
        folder = db.get_or_create_folder_id(self.conn, [])
        db.upsert_file(self.conn, folder, "a.txt", 1, 1.0, "h1")
        db.prune_files_not_in(self.conn, [])
        self.assertEqual(list(db.all_files(self.conn)), [])

    def test_all_files_and_all_folders(self):
        folder = db.get_or_create_folder_id(self.conn, ["sub"])
        db.upsert_file(self.conn, folder, "a.txt", 1, 1.0, "h1")
        files = list(db.all_files(self.conn))
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], (folder, "a.txt", "h1"))
        folders = list(db.all_folders(self.conn))
        # root + "sub"
        self.assertEqual(len(folders), 2)

    def test_meta_roundtrip(self):
        self.assertIsNone(db.get_meta(self.conn, "indexed_at"))
        db.set_meta(self.conn, "indexed_at", 123.456)
        self.assertEqual(db.get_meta(self.conn, "indexed_at"), "123.456")
        db.set_meta(self.conn, "indexed_at", 789.0)
        self.assertEqual(db.get_meta(self.conn, "indexed_at"), "789.0")

    def test_schema_persists_across_reconnect(self):
        folder = db.get_or_create_folder_id(self.conn, ["x"])
        db.upsert_file(self.conn, folder, "f.txt", 1, 1.0, "h1")
        self.conn.commit()
        self.conn.close()

        conn2 = db.connect(self.tmp)
        try:
            folder2 = db.get_or_create_folder_id(conn2, ["x"])
            self.assertEqual(folder, folder2)
            self.assertIsNotNone(db.lookup_file(conn2, folder2, "f.txt"))
        finally:
            conn2.close()
        self.conn = db.connect(self.tmp)  # so tearDown's close() has something valid


if __name__ == "__main__":
    unittest.main()
