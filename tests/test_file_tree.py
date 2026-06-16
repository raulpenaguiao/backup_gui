import os
import shutil
import tempfile
import unittest

from tools_library.file_tree import human_size, build_size_index
from tools_library.drive_variables import pigmy_hash_file


class TestHumanSize(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(human_size(512), "512.0 B")

    def test_kilobytes(self):
        self.assertEqual(human_size(1024), "1.0 KB")

    def test_megabytes(self):
        self.assertEqual(human_size(1024 ** 2), "1.0 MB")

    def test_gigabytes(self):
        self.assertEqual(human_size(1024 ** 3), "1.0 GB")


class TestBuildSizeIndex(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write(self, rel_path, content=b"x"):
        path = os.path.join(self.tmp, rel_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)
        return path

    def test_empty_vault(self):
        sizes, counts = build_size_index(self.tmp)
        self.assertEqual(sizes[self.tmp], 0)
        self.assertEqual(counts[self.tmp], 0)

    def test_single_file_size(self):
        self._write("a.txt", b"hello")
        sizes, counts = build_size_index(self.tmp)
        self.assertEqual(sizes[os.path.join(self.tmp, "a.txt")], 5)
        self.assertEqual(sizes[self.tmp], 5)
        self.assertEqual(counts[self.tmp], 1)

    def test_nested_dir_aggregation(self):
        self._write("sub/b.txt", b"123")
        sizes, counts = build_size_index(self.tmp)
        sub = os.path.join(self.tmp, "sub")
        self.assertEqual(sizes[sub], 3)
        self.assertEqual(sizes[self.tmp], 3)
        self.assertEqual(counts[self.tmp], 1)

    def test_multiple_files(self):
        self._write("a.txt", b"ab")
        self._write("b.txt", b"cde")
        sizes, counts = build_size_index(self.tmp)
        self.assertEqual(sizes[self.tmp], 5)
        self.assertEqual(counts[self.tmp], 2)

    def test_skips_pigmy_hash_file(self):
        self._write(pigmy_hash_file, b"should be skipped by index")
        self._write("real.txt", b"ab")
        sizes, counts = build_size_index(self.tmp)
        self.assertEqual(sizes[self.tmp], 2)
        self.assertEqual(counts[self.tmp], 1)

    def test_skips_pigmy_hash_db_sidecar_files(self):
        self._write(pigmy_hash_file + "-journal", b"stale journal from a crashed run")
        self._write("real.txt", b"ab")
        sizes, counts = build_size_index(self.tmp)
        self.assertEqual(sizes[self.tmp], 2)
        self.assertEqual(counts[self.tmp], 1)

    def test_skips_pigmy_dir(self):
        self._write(".pigmy/data", b"skip")
        self._write("real.txt", b"ok")
        sizes, counts = build_size_index(self.tmp)
        self.assertEqual(sizes[self.tmp], 2)
        self.assertEqual(counts[self.tmp], 1)


if __name__ == "__main__":
    unittest.main()
