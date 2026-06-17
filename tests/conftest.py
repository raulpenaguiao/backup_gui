import os
import shutil
import tempfile

import pytest

import tools_library.tracer as tracer
from tools_library import path_db, deleted_files_db


@pytest.fixture(autouse=True)
def isolate_log_and_dbs():
    """Redirect tracer's log folder and the path/deleted-files SQLite DBs to a
    temp directory for every test. Without this, running the suite writes
    real entries into the project's log/ folder (including deliberately
    triggered errors from tests like test_unreadable_file_triggers_real_os_error),
    which is indistinguishable from genuine application errors when someone
    later opens the log viewer.
    """
    tmp = tempfile.mkdtemp()
    orig_log_folder = tracer.log_folder_path
    orig_paths_db = path_db.PATHS_DB_FILE
    orig_deleted_db = deleted_files_db.DELETED_FILES_DB_FILE

    tracer.log_folder_path = tmp
    path_db.PATHS_DB_FILE = os.path.join(tmp, "paths.db")
    deleted_files_db.DELETED_FILES_DB_FILE = os.path.join(tmp, "deleted_files.db")
    path_db.clear_cache()

    try:
        yield
    finally:
        tracer.log_folder_path = orig_log_folder
        path_db.PATHS_DB_FILE = orig_paths_db
        deleted_files_db.DELETED_FILES_DB_FILE = orig_deleted_db
        path_db.clear_cache()
        shutil.rmtree(tmp, ignore_errors=True)
