from conftest import login


def test_register_creates_student_and_logs_in(anon):
    res = anon.post("/api/auth/register", json={"name": "Jasmine", "email": "Jas@WSSU.edu", "password": "longenough"})
    assert res.status_code == 201
    assert res.get_json()["user"]["role"] == "student"
    me = anon.get("/api/auth/me").get_json()["user"]
    assert me["email"] == "jas@wssu.edu"  # emails are stored lowercase


def test_register_rejects_bad_input(anon):
    res = anon.post("/api/auth/register", json={"name": "", "email": "nope", "password": "short"})
    assert res.status_code == 400
    assert set(res.get_json()["fields"]) == {"name", "email", "password"}


def test_register_rejects_duplicate_email(anon):
    res = anon.post("/api/auth/register", json={"name": "X", "email": "student@demo.edu", "password": "longenough"})
    assert res.status_code == 400
    assert "email" in res.get_json()["fields"]


def test_register_cannot_choose_staff_role(anon):
    res = anon.post("/api/auth/register", json={"name": "Sneaky", "email": "s@wssu.edu", "password": "longenough", "role": "admin"})
    assert res.get_json()["user"]["role"] == "student"


def test_login_wrong_password(anon):
    res = anon.post("/api/auth/login", json={"email": "student@demo.edu", "password": "wrong"})
    assert res.status_code == 401


def test_logout_ends_session(student):
    student.post("/api/auth/logout")
    assert student.get("/api/auth/me").status_code == 401


def test_api_requires_login(anon):
    assert anon.get("/api/tickets").status_code == 401


def test_pages_redirect_to_login(anon):
    res = anon.get("/tickets")
    assert res.status_code == 302 and res.headers["Location"].endswith("/login")


def test_role_home_pages(app):
    assert login(app.test_client(), "student@demo.edu").get("/").headers["Location"].endswith("/tickets")
    assert login(app.test_client(), "staff@demo.edu").get("/").headers["Location"].endswith("/queue")
