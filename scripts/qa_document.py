"""Build an internal QA document from a completed integration-test run."""
import json
import sqlite3
from pathlib import Path

from workbench.reports import generate_note

database = next(Path("tmp/pytest").glob("test_three*/data/workbench.sqlite3"))
with sqlite3.connect(database) as connection:
    row = connection.execute("SELECT state FROM jobs WHERE status=? LIMIT 1", ("completed",)).fetchone()
state = json.loads(row[0])
generate_note(state, Path("tmp/qa/inspection-draft.docx"))
print("Created QA draft from the tested workflow state")
