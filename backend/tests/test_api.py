import os

os.environ["DATABASE_URL"] = "sqlite:///./test_student_cloud.db"
os.environ["JWT_SECRET"] = "test-secret"

from fastapi.testclient import TestClient
from app.main import app


def test_health_and_login():
    with TestClient(app) as client:
        ready = client.get("/health/ready")
        assert ready.status_code == 200
        assert ready.json()["database"] == "connected"
        login = client.post("/api/v1/auth/login", json={"email": "admin@studentsphere.edu", "password": "Admin@123"})
        assert login.status_code == 200
        assert login.json()["user"]["role"] == "admin"


def test_protected_dashboard():
    with TestClient(app) as client:
        login = client.post("/api/v1/auth/login", json={"email": "teacher@studentsphere.edu", "password": "Teacher@123"}).json()
        dashboard = client.get("/api/v1/dashboard", headers={"Authorization": f"Bearer {login['access_token']}"})
        assert dashboard.status_code == 200
        assert dashboard.json()["kpis"]["students"] >= 4

