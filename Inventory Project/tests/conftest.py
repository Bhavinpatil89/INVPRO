import pytest
from app import create_app
from app.core.db import init_db


@pytest.fixture
def app():
    # Set testing config

    
    app = create_app()
    app.config.update({
        "TESTING": True,
    })

    # Initialize test DB
    with app.app_context():
        init_db()

    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()
