"""Shared pytest fixtures: throwaway SQLite DB + Flask test client.

The DB file is created fresh per test session and removed after — tests
never touch the real fixzy.db.
"""
import os
import sys
import tempfile

import pytest

# Configure env BEFORE importing the app (config reads env at import time)
_tmp = tempfile.NamedTemporaryFile(  # noqa: SIM115 - name kept for the DB URI
    suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["ADMIN_USER"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test-admin-pw"
os.environ["BREVO_WEBHOOK_SECRET"] = ""  # start unset; tests set via DB

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def app():
    import app as app_module
    with app_module.app.app_context():
        from models import db
        db.create_all()
        yield app_module.app
        db.drop_all()
    os.unlink(_tmp.name)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_client(client):
    """Client already authenticated as admin."""
    client.auth = ("admin", "test-admin-pw")
    return _AuthClient(client)


class _AuthClient:
    def __init__(self, client):
        self.client = client

    def get(self, url, **kw):
        return self.client.get(url, auth=("admin", "test-admin-pw"), **kw)

    def post(self, url, **kw):
        return self.client.post(url, auth=("admin", "test-admin-pw"), **kw)


@pytest.fixture()
def db_session(app):
    from models import db
    with app.app_context():
        yield db
        # Roll back everything each test leaves behind
        db.session.rollback()
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
