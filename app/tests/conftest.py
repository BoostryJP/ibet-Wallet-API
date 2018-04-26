# -*- coding: utf-8 -*-
import pytest
from falcon import testing

from app import config
from app.main import App
from app.middleware import JSONTranslator, DatabaseSessionManager
from app.database import db_session, init_session, engine

@pytest.fixture(scope = 'session')
def client():
    config.DB_AUTOCOMMIT = False
    
    init_session()
    middleware = [JSONTranslator(), DatabaseSessionManager(db_session)]
    return testing.TestClient(App(middleware=middleware))

# テーブルの自動作成・自動削除
@pytest.fixture(scope = 'session')
def db(request):
    from app.model import Base
    Base.metadata.create_all(engine)

    def teardown():
        Base.metadata.drop_all(engine)
        return

    request.addfinalizer(teardown)
    return db_session

# セッションの作成・自動ロールバック
@pytest.fixture(scope = 'function')
def session(request, db):
    session = db_session()

    def teardown():
        session.rollback()

    request.addfinalizer(teardown)
    return session
