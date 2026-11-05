import pytest

from app import create_app

PASSWORD = "password123"


@pytest.fixture
def app(tmp_path):
    return create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.db"),
        "SECRET_KEY": "test",
        "SEED_DEMO": True,
        "DEMO_PASSWORD": PASSWORD,
    })


def login(client, email, password=PASSWORD):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.get_json()
    return client


@pytest.fixture
def student(app):
    return login(app.test_client(), "student@demo.edu")


@pytest.fixture
def staff(app):
    return login(app.test_client(), "staff@demo.edu")


@pytest.fixture
def admin(app):
    return login(app.test_client(), "admin@demo.edu")


@pytest.fixture
def anon(app):
    return app.test_client()


def make_ticket(client, **overrides):
    data = {"title": "Can't log in", "description": "Account locked", "category": "account", "priority": "high"}
    data.update(overrides)
    res = client.post("/api/tickets", json=data)
    assert res.status_code == 201, res.get_json()
    return res.get_json()["ticket"]
