def test_create_department_employee_and_get_tree(client):
    root_response = client.post("/departments/", json={"name": " IT "})
    assert root_response.status_code == 201
    root = root_response.json()
    assert root["name"] == "IT"

    child_response = client.post(
        "/departments/",
        json={"name": "Backend", "parent_id": root["id"]},
    )
    assert child_response.status_code == 201
    child = child_response.json()

    employee_response = client.post(
        f"/departments/{child['id']}/employees/",
        json={"full_name": " Ivan Ivanov ", "position": " Developer "},
    )
    assert employee_response.status_code == 201
    employee = employee_response.json()
    assert employee["full_name"] == "Ivan Ivanov"
    assert employee["position"] == "Developer"

    tree_response = client.get(f"/departments/{root['id']}?depth=2&include_employees=true")
    assert tree_response.status_code == 200
    tree = tree_response.json()
    assert tree["department"]["name"] == "IT"
    assert tree["children"][0]["department"]["name"] == "Backend"
    assert tree["children"][0]["employees"][0]["full_name"] == "Ivan Ivanov"


def test_prevent_move_department_inside_own_subtree(client):
    root = client.post("/departments/", json={"name": "Root"}).json()
    child = client.post(
        "/departments/",
        json={"name": "Child", "parent_id": root["id"]},
    ).json()

    response = client.patch(
        f"/departments/{root['id']}",
        json={"parent_id": child["id"]},
    )

    assert response.status_code == 409
    assert "subtree" in response.json()["detail"]


def test_duplicate_name_in_same_parent_returns_409(client):
    root = client.post("/departments/", json={"name": "Root"}).json()
    first = client.post(
        "/departments/",
        json={"name": "Backend", "parent_id": root["id"]},
    )
    assert first.status_code == 201

    second = client.post(
        "/departments/",
        json={"name": "Backend", "parent_id": root["id"]},
    )
    assert second.status_code == 409


def test_duplicate_name_in_different_parents_is_allowed(client):
    root_a = client.post("/departments/", json={"name": "Root A"}).json()
    root_b = client.post("/departments/", json={"name": "Root B"}).json()

    first = client.post(
        "/departments/",
        json={"name": "Backend", "parent_id": root_a["id"]},
    )
    second = client.post(
        "/departments/",
        json={"name": "Backend", "parent_id": root_b["id"]},
    )

    assert first.status_code == 201
    assert second.status_code == 201


def test_delete_reassign_moves_employees(client):
    source = client.post("/departments/", json={"name": "Source"}).json()
    target = client.post("/departments/", json={"name": "Target"}).json()

    employee_response = client.post(
        f"/departments/{source['id']}/employees/",
        json={"full_name": "Anna Petrova", "position": "QA"},
    )
    assert employee_response.status_code == 201

    delete_response = client.delete(
        f"/departments/{source['id']}?mode=reassign&reassign_to_department_id={target['id']}"
    )
    assert delete_response.status_code == 204

    target_tree_response = client.get(f"/departments/{target['id']}?depth=0&include_employees=true")
    assert target_tree_response.status_code == 200
    employees = target_tree_response.json()["employees"]
    assert len(employees) == 1
    assert employees[0]["full_name"] == "Anna Petrova"

    deleted_response = client.get(f"/departments/{source['id']}")
    assert deleted_response.status_code == 404
