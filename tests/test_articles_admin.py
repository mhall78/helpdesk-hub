from conftest import make_ticket


def test_anyone_can_search_articles(anon):
    res = anon.get("/api/articles?q=password")
    titles = [a["title"] for a in res.get_json()["articles"]]
    assert "How to reset your campus password" in titles
    assert "Installing licensed software" not in titles  # doesn't mention passwords


def test_staff_creates_and_edits_article(staff, anon):
    res = staff.post("/api/articles", json={"title": "Printing on campus", "body": "Steps...", "category": "hardware"})
    assert res.status_code == 201
    aid = res.get_json()["article"]["id"]
    res = staff.put(f"/api/articles/{aid}", json={"title": "Printing from a laptop", "body": "New steps", "category": "hardware"})
    assert res.get_json()["article"]["title"] == "Printing from a laptop"
    assert anon.get(f"/api/articles/{aid}").get_json()["article"]["body"] == "New steps"


def test_students_cannot_write_articles(student):
    res = student.post("/api/articles", json={"title": "x", "body": "y"})
    assert res.status_code == 403


def test_article_validation(staff):
    res = staff.post("/api/articles", json={"title": "", "body": ""})
    assert res.status_code == 400


def test_admin_stats(student, staff, admin):
    a = make_ticket(student, category="account")
    make_ticket(student, category="wifi")
    staff.patch(f"/api/tickets/{a['id']}", json={"status": "resolved"})
    s = admin.get("/api/admin/stats").get_json()
    assert s["total"] == 2
    assert s["by_status"]["resolved"] == 1 and s["by_status"]["open"] == 1
    assert s["by_category"]["wifi"] == 1
    assert s["resolved_count"] == 1 and s["avg_resolution_hours"] is not None
    assert s["unassigned_open"] == 1


def test_stats_admin_only(staff):
    assert staff.get("/api/admin/stats").status_code == 403


def test_all_pages_render(app, admin, anon):
    for path in ("/login", "/register", "/kb"):
        assert anon.get(path).status_code == 200
    for path in ("/queue", "/kb", "/admin"):
        assert admin.get(path).status_code == 200
    t = make_ticket(admin)
    assert admin.get(f"/tickets/{t['id']}").status_code == 200


def test_health(anon):
    assert anon.get("/health").get_json() == {"status": "ok"}


def test_html_404_for_pages_json_for_api(anon):
    assert anon.get("/nope").mimetype == "text/html"
    assert anon.get("/api/nope").get_json()["error"]
