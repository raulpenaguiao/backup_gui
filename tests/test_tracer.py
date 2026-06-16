import os
import shutil
import tempfile
import unittest

import tools_library.tracer as tracer
from tools_library import path_db


class TestTracer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig_log_folder = tracer.log_folder_path
        self._orig_level = tracer.TRACE_LEVEL
        self._orig_paths_db = path_db.PATHS_DB_FILE
        tracer.log_folder_path = self.tmp
        path_db.PATHS_DB_FILE = os.path.join(self.tmp, "paths.db")
        path_db.clear_cache()

    def tearDown(self):
        tracer.log_folder_path = self._orig_log_folder
        tracer.TRACE_LEVEL = self._orig_level
        path_db.PATHS_DB_FILE = self._orig_paths_db
        path_db.clear_cache()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _read_log(self):
        path = tracer.current_log_path()
        if not os.path.exists(path):
            return ""
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_level_filtering_suppresses_above_threshold(self):
        tracer.TRACE_LEVEL = 2
        tracer.log("verbose line", trace_level=3)
        tracer.log("visible line", trace_level=2)
        content = self._read_log()
        self.assertNotIn("verbose line", content)
        self.assertIn("visible line", content)

    def test_level_written_into_line(self):
        tracer.TRACE_LEVEL = 5
        tracer.log("tagged", trace_level=4)
        self.assertIn("L4 ", self._read_log())

    def test_default_level_respects_low_threshold(self):
        tracer.TRACE_LEVEL = 0
        tracer.log("should be suppressed")
        self.assertNotIn("should be suppressed", self._read_log())

    def test_pid_round_trips_through_path_db(self):
        p = os.path.join(self.tmp, "sub", "file.txt")
        token = tracer.pid(p)
        self.assertTrue(token.startswith("#"))
        resolved_id = int(token[1:])
        self.assertEqual(os.path.normpath(path_db.resolve_path(resolved_id)), os.path.normpath(p))

    def test_pid_empty_for_falsy_path(self):
        self.assertEqual(tracer.pid(""), "")
        self.assertEqual(tracer.pid(None), "")

    def test_log_error_writes_both_files_always(self):
        tracer.TRACE_LEVEL = 0  # even at the lowest threshold, errors must still appear
        tracer.log_error("boom")
        with open(tracer.current_error_log_path(), encoding="utf-8") as f:
            error_content = f.read()
        self.assertIn("boom", error_content)
        self.assertIn("ERROR boom", self._read_log())


if __name__ == "__main__":
    unittest.main()
