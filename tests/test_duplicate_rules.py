import os
import shutil
import tempfile
import unittest

from tools_library.duplicate_rules import (
    load_rules, save_rules, add_rule, remove_rule,
    file_matches_rule, apply_rules, net_action,
)


def _make_rule(rtype, pattern, action="delete", name="test"):
    return {"name": name, "action": action, "type": rtype, "pattern": pattern}


class TestLoadSave(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_load_empty_when_no_file(self):
        self.assertEqual(load_rules(self.tmp), [])

    def test_roundtrip(self):
        rules = [_make_rule("path_contains", ".git")]
        save_rules(self.tmp, rules)
        self.assertEqual(load_rules(self.tmp), rules)

    def test_add_and_remove(self):
        add_rule(self.tmp, _make_rule("extension", ".tmp"))
        add_rule(self.tmp, _make_rule("in_folder", "notes"))
        rules = load_rules(self.tmp)
        self.assertEqual(len(rules), 2)
        remove_rule(self.tmp, 0)
        rules = load_rules(self.tmp)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["pattern"], "notes")

    def test_remove_out_of_range_is_safe(self):
        add_rule(self.tmp, _make_rule("extension", ".tmp"))
        remove_rule(self.tmp, 99)
        self.assertEqual(len(load_rules(self.tmp)), 1)


class TestFileMatchesRule(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _fp(self, rel):
        return os.path.join(self.tmp, rel.replace("/", os.sep))

    # path_contains
    def test_path_contains_match(self):
        rule = _make_rule("path_contains", ".git")
        self.assertTrue(file_matches_rule(rule, self._fp("notes/.git/config"), self.tmp))

    def test_path_contains_no_match(self):
        rule = _make_rule("path_contains", ".git")
        self.assertFalse(file_matches_rule(rule, self._fp("notes/readme.md"), self.tmp))

    def test_path_contains_case_insensitive(self):
        rule = _make_rule("path_contains", ".GIT")
        self.assertTrue(file_matches_rule(rule, self._fp("project/.git/HEAD"), self.tmp))

    # path_regex
    def test_path_regex_match(self):
        rule = _make_rule("path_regex", r"^notes/.*\.bak$")
        self.assertTrue(file_matches_rule(rule, self._fp("notes/old.bak"), self.tmp))

    def test_path_regex_no_match(self):
        rule = _make_rule("path_regex", r"^notes/.*\.bak$")
        self.assertFalse(file_matches_rule(rule, self._fp("archive/old.bak"), self.tmp))

    # in_folder
    def test_in_folder_match(self):
        rule = _make_rule("in_folder", "notes/archive")
        self.assertTrue(file_matches_rule(rule, self._fp("notes/archive/old.txt"), self.tmp))

    def test_in_folder_nested_match(self):
        rule = _make_rule("in_folder", "notes")
        self.assertTrue(file_matches_rule(rule, self._fp("notes/sub/file.txt"), self.tmp))

    def test_in_folder_no_match(self):
        rule = _make_rule("in_folder", "notes/archive")
        self.assertFalse(file_matches_rule(rule, self._fp("notes/active/file.txt"), self.tmp))

    def test_in_folder_prefix_not_confused(self):
        rule = _make_rule("in_folder", "notes")
        self.assertFalse(file_matches_rule(rule, self._fp("notes_old/file.txt"), self.tmp))

    # extension
    def test_extension_match_with_dot(self):
        rule = _make_rule("extension", ".tmp")
        self.assertTrue(file_matches_rule(rule, self._fp("work/file.tmp"), self.tmp))

    def test_extension_match_without_dot(self):
        rule = _make_rule("extension", "tmp")
        self.assertTrue(file_matches_rule(rule, self._fp("work/file.tmp"), self.tmp))

    def test_extension_no_match(self):
        rule = _make_rule("extension", ".tmp")
        self.assertFalse(file_matches_rule(rule, self._fp("work/file.txt"), self.tmp))

    def test_extension_case_insensitive(self):
        rule = _make_rule("extension", ".TMP")
        self.assertTrue(file_matches_rule(rule, self._fp("work/file.tmp"), self.tmp))


class TestApplyRules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _fp(self, rel):
        return os.path.join(self.tmp, rel.replace("/", os.sep))

    def test_no_rules_returns_empty_lists(self):
        paths = [self._fp("file.txt")]
        result = apply_rules([], paths, self.tmp)
        self.assertEqual(result[paths[0]], [])

    def test_single_rule_match(self):
        rules = [_make_rule("extension", ".tmp", action="delete", name="Delete temps")]
        paths = [self._fp("file.tmp"), self._fp("file.txt")]
        result = apply_rules(rules, paths, self.tmp)
        self.assertEqual(len(result[paths[0]]), 1)
        self.assertEqual(result[paths[0]][0], ("Delete temps", "delete"))
        self.assertEqual(result[paths[1]], [])

    def test_multiple_rules_multiple_matches(self):
        rules = [
            _make_rule("extension", ".tmp", action="delete"),
            _make_rule("path_contains", "archive", action="delete"),
        ]
        paths = [self._fp("archive/file.tmp")]
        result = apply_rules(rules, paths, self.tmp)
        self.assertEqual(len(result[paths[0]]), 2)


class TestNetAction(unittest.TestCase):
    def test_none_when_no_matches(self):
        self.assertIsNone(net_action([]))

    def test_delete_when_only_delete(self):
        self.assertEqual(net_action([("r1", "delete"), ("r2", "delete")]), "delete")

    def test_keep_when_only_keep(self):
        self.assertEqual(net_action([("r1", "keep")]), "keep")

    def test_conflict_when_both(self):
        self.assertEqual(net_action([("r1", "delete"), ("r2", "keep")]), "conflict")


if __name__ == "__main__":
    unittest.main()
