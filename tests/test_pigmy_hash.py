import os
import shutil
import tempfile
import unittest

from tools_library.pigmy_hash import compute_file_hash, save_pigmy_hash, load_pigmy_hash


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
        loaded = load_pigmy_hash(self.tmp)
        self.assertEqual(original, loaded)

    def test_empty_hash_roundtrip(self):
        save_pigmy_hash(self.tmp, {})
        self.assertEqual(load_pigmy_hash(self.tmp), {})


if __name__ == "__main__":
    unittest.main()
