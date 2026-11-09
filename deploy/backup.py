import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from shutil import copyfileobj
from tempfile import TemporaryDirectory

database = Path(os.environ["DJANGO_DB_PATH"])
with TemporaryDirectory() as directory:
    snapshot = Path(directory) / "snapshot.sqlite3"
    with (
        closing(sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)) as source,
        closing(sqlite3.connect(snapshot)) as target,
    ):
        source.backup(target)
    with snapshot.open("rb") as file:
        copyfileobj(file, sys.stdout.buffer)
