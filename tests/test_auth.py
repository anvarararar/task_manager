from fastapi.testclient import TestClient
import faker
from app.main import app
from datetime import date, timedelta

client = TestClient(app)
fake = faker.Faker()

client.fake_user_email = fake.email()
client.fake_user_password = fake.password()
client.fake_user_name = fake.first_name()
client.new_user_id = 0
client.auth_token = ""
task_id = 0
test_statuses = ["open", "in_progress", "closed"]

def test_signup():
    response = client.post("/auth/signup",
                           json={"email": client.fake_user_email,
                                 "password": client.fake_user_password,
                                 "name": client.fake_user_name}
    )
    assert response.status_code == 201
    client.new_user_id = response.json()


def test_login():
    response = client.post("/auth/login",
                           data={"username": client.fake_user_email,
                                 "password": client.fake_user_password}
    )
    assert response.status_code == 200
    client.auth_token = response.json()['access_token']


def test_me():
    response = client.get("/utils/me", headers={"Authorization": f"Bearer {client.auth_token}"})
    assert response.status_code == 200
    assert response.json() == client.new_user_id

def test_get_projects(): 
    response = client.get("/projects")
    assert response.status_code == 200

def test_create_project():
    response = client.post("/projects", headers={"Authorization": f"Bearer {client.auth_token}"},
                           json={"project_description": fake.street_address(),
                                 "project_name": client.fake_user_name
                            }
    )
    assert response.status_code == 201
    global project_id
    project_id = response.json()["project_id"] 

def test_update_project_by_id():
    response = client.patch(f"/projects/{project_id}", headers={"Authorization": f"Bearer {client.auth_token}"}, json={"project_description": fake.street_address()})
    assert response.status_code == 200

def test_create_task():
    response = client.post("/tasks", headers={"Authorization": f"Bearer {client.auth_token}"},
                           json={"task_description": fake.street_address(),
                                 "due_date": str(fake.date_between(date.today(), timedelta(days=30))),
                                 "assignee": 1,
                                 "task_status": "open",
                                 "project": project_id
                            }
    )
    assert response.status_code == 201
    global task_id
    task_id = response.json()["task_id"]

def test_get_tasks():
    response = client.get("/tasks")
    assert response.status_code == 200

def test_get_task_by_id():
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200

def test_update_task():
    response = client.patch(f"/tasks/{task_id}", headers={"Authorization": f"Bearer {client.auth_token}"}, json={"task_description": fake.street_address()})
    assert response.status_code == 200

def test_delete_task():
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 200 

def test_get_project_statistics():
    response = client.get(f"/projects/{project_id}/statistics")
    assert response.status_code == 200

def test_get_latest_stats_snapshot():
    response = client.get(f"/projects/{project_id}/statistics/latest?snapshot_date=" + str(date.today()))
    assert response.status_code == 200

def test_get_task_delta_in_period():
    response = client.get(f"/projects/{project_id}/task_delta?start_date=2024-05-20&end_date=2024-05-21")
    assert response.status_code == 200