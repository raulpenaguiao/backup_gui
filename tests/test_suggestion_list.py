import unittest

from tools_library.suggestion_list import SuggestionList


class TestSuggestionList(unittest.TestCase):
    def test_add_returns_item(self):
        s = SuggestionList()
        item = s.add("/ev/a.txt", 10, "h1", "/main/a.txt", "copy of main vault file")
        self.assertEqual(item["path"], "/ev/a.txt")
        self.assertEqual(len(s), 1)

    def test_same_path_suggested_twice_is_ignored(self):
        """The exact bug report: a file matched by both 'Copies in EV detection'
        (copy of a main-vault file) AND 'Double files in EV' (the non-kept half
        of an internal duplicate pair) must only be suggested once."""
        s = SuggestionList()
        first = s.add("/ev/b.txt", 10, "h1", "/main/m.txt", "copy of main vault file")
        second = s.add("/ev/b.txt", 10, "h1", "/ev/a.txt", "duplicate within EV")
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(len(s), 1)
        # The original entry (from the first detection step) is kept as-is.
        self.assertEqual(list(s)[0]["copy_path"], "/main/m.txt")

    def test_retry_does_not_duplicate(self):
        """Re-running the same detection step (e.g. after Retry) re-matches the
        same files — they must not pile up as duplicate entries."""
        s = SuggestionList()
        s.add("/ev/a.txt", 5, "h1", "/main/a.txt", "copy of main vault file")
        s.add("/ev/a.txt", 5, "h1", "/main/a.txt", "copy of main vault file")
        self.assertEqual(len(s), 1)

    def test_different_paths_both_added(self):
        s = SuggestionList()
        s.add("/ev/a.txt", 5, "h1", None, "reason")
        s.add("/ev/b.txt", 7, "h2", None, "reason")
        self.assertEqual(len(s), 2)

    def test_total_size(self):
        s = SuggestionList()
        s.add("/ev/a.txt", 5, "h1", None, "reason")
        s.add("/ev/b.txt", 7, "h2", None, "reason")
        self.assertEqual(s.total_size(), 12)

    def test_remove_paths(self):
        s = SuggestionList()
        s.add("/ev/a.txt", 5, "h1", None, "reason")
        s.add("/ev/b.txt", 7, "h2", None, "reason")
        s.remove_paths(["/ev/a.txt"])
        self.assertEqual(len(s), 1)
        self.assertEqual(list(s)[0]["path"], "/ev/b.txt")

    def test_remove_then_readd_path_is_allowed(self):
        """Once a path is removed (deleted), the same path should be addable
        again rather than being permanently blacklisted."""
        s = SuggestionList()
        s.add("/ev/a.txt", 5, "h1", None, "reason")
        s.remove_paths(["/ev/a.txt"])
        item = s.add("/ev/a.txt", 5, "h1", None, "reason again")
        self.assertIsNotNone(item)
        self.assertEqual(len(s), 1)

    def test_snapshot_is_deduplicated_and_independent(self):
        s = SuggestionList()
        s.add("/ev/a.txt", 5, "h1", None, "reason")
        snap = s.snapshot()
        self.assertEqual(len(snap), 1)
        # Mutating the snapshot list must not affect the live SuggestionList.
        snap.append({"path": "/ev/fake.txt", "size": 0, "hash": None,
                    "copy_path": None, "reason": "injected"})
        self.assertEqual(len(s), 1)

    def test_iteration_and_len(self):
        s = SuggestionList()
        self.assertEqual(len(s), 0)
        self.assertEqual(list(s), [])
        s.add("/ev/a.txt", 5, "h1", None, "reason")
        self.assertEqual(len(list(s)), 1)


if __name__ == "__main__":
    unittest.main()
