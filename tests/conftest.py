"""Gemeinsame Pytest-Fixtures für alle Tests."""
import os

# DB in temporäres Verzeichnis umleiten – muss vor src-Imports gesetzt sein
def pytest_configure(config):
    import tempfile
    tmp = tempfile.mkdtemp(prefix="raumzeit_test_")
    os.environ.setdefault("DB_DIR", tmp)
