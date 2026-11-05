from conftest import make_ticket


def test_student_submits_and_sees_ticket(student):
    t = make_ticket(student)
    assert t["status"] == "open" and t["assigned_to"] is None
    tickets = student.get("/api/tickets").get_json()["tickets"]
    assert [x["id"] for x in tickets] == [t["id"]]


def test_ticket_validation(student):
    res = student.post("/api/tickets", json={"title": "", "description": "", "category": "pizza", "priority": "urgent"})
    assert res.status_code == 400
    assert set(res.get_json()["fields"]) == {"title", "description", "category", "priority"}


def test_students_cannot_see_each_others_tickets(app, student):
    t = make_ticket(student)
    other = app.test_client()
    other.post("/api/auth/register", json={"name": "Other", "email": "o@wssu.edu", "password": "longenough"})
    assert other.get("/api/tickets").get_json()["tickets"] == []
    assert other.get(f"/api/tickets/{t['id']}").status_code == 404
    assert other.post(f"/api/tickets/{t['id']}/comments", json={"body": "hi"}).status_code == 404


def test_staff_queue_sorts_high_priority_first(student, staff):
    low = make_ticket(student, priority="low")
    high = make_ticket(student, priority="high")
    ids = [x["id"] for x in staff.get("/api/tickets").get_json()["tickets"]]
    assert ids == [high["id"], low["id"]]


def test_staff_filters(student, staff):
    make_ticket(student, category="wifi", priority="low")
    make_ticket(student, category="account")
    wifi = staff.get("/api/tickets?category=wifi").get_json()["tickets"]
    assert len(wifi) == 1 and wifi[0]["category"] == "wifi"
    assert staff.get("/api/tickets?status=bogus").status_code == 400


def test_claim_sets_assignee_and_starts_work(student, staff):
    t = make_ticket(student)
    res = staff.patch(f"/api/tickets/{t['id']}", json={"assigned_to": "me"})
    ticket = res.get_json()["ticket"]
    assert ticket["assignee_name"] == "Demo Staff"
    assert ticket["status"] == "in_progress"
    mine = staff.get("/api/tickets?assigned=me").get_json()["tickets"]
    assert [x["id"] for x in mine] == [t["id"]]


def test_resolve_with_note(student, staff):
    t = make_ticket(student)
    res = staff.patch(f"/api/tickets/{t['id']}", json={"status": "resolved", "note": "Unlocked your account."})
    assert res.get_json()["ticket"]["resolved_at"] is not None
    detail = student.get(f"/api/tickets/{t['id']}").get_json()["ticket"]
    assert detail["status"] == "resolved"
    assert detail["comments"][0]["body"] == "Unlocked your account."
    assert detail["comments"][0]["author_role"] == "staff"


def test_reopen_clears_resolved_at(student, staff):
    t = make_ticket(student)
    staff.patch(f"/api/tickets/{t['id']}", json={"status": "resolved"})
    res = staff.patch(f"/api/tickets/{t['id']}", json={"status": "open"})
    assert res.get_json()["ticket"]["resolved_at"] is None


def test_students_cannot_update_tickets(student):
    t = make_ticket(student)
    assert student.patch(f"/api/tickets/{t['id']}", json={"status": "closed"}).status_code == 403


def test_cannot_assign_to_a_student(app, student, staff):
    t = make_ticket(student)
    student_id = student.get("/api/auth/me").get_json()["user"]["id"]
    res = staff.patch(f"/api/tickets/{t['id']}", json={"assigned_to": student_id})
    assert res.status_code == 400


def test_comment_thread(student, staff):
    t = make_ticket(student)
    staff.post(f"/api/tickets/{t['id']}/comments", json={"body": "Which error do you see?"})
    student.post(f"/api/tickets/{t['id']}/comments", json={"body": "Error 403"})
    bodies = [c["body"] for c in student.get(f"/api/tickets/{t['id']}").get_json()["ticket"]["comments"]]
    assert bodies == ["Which error do you see?", "Error 403"]
    assert student.post(f"/api/tickets/{t['id']}/comments", json={"body": "  "}).status_code == 400


def test_missing_ticket(staff):
    assert staff.get("/api/tickets/999").status_code == 404
