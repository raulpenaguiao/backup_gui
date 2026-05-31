import os
import tempfile
import unittest

from tools_library.vault_operations import get_repetitions


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


if __name__ == "__main__":
    unittest.main()
