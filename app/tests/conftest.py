# -*- coding: utf-8 -*-
import pytest
from falcon import testing

from app.main import App
from app.middleware import JSONTranslator, DatabaseSessionManager
from app.database import db_session, init_session

@pytest.fixture(scope = 'module')
def client():
    init_session()
    middleware = [JSONTranslator(), DatabaseSessionManager(db_session)]
    return testing.TestClient(App(middleware=middleware))
