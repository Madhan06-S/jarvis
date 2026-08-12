from pathlib import Path
from typing import Dict
from jinja2 import Template
from spec_engine import AppSpec

class TestGenerator:
    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self):
        return {
            "conftest": Template("""
import pytest
from fastapi.testclient import TestClient
from main import app
from database import Base, engine, SessionLocal

@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
"""),
            "model_test": Template("""
import pytest

def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_and_list_{{model.name.lower()}}(client):
    # Test create
    payload = {}
    {% for field in model.fields if field.name not in ["id", "created_at", "updated_at", "deleted_at"] %}
    {% if field.type == "number" %}
    payload["{{field.name}}"] = 10.0
    {% elif field.type == "boolean" %}
    payload["{{field.name}}"] = True
    {% elif field.type == "email" %}
    payload["{{field.name}}"] = "test_{{field.name}}@example.com"
    {% else %}
    payload["{{field.name}}"] = "Sample {{field.name}}"
    {% endif %}
    {% endfor %}

    res = client.post("/api/{{model.name.lower()}}s", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "data" in data
    created_id = data["data"]["id"]

    # Test list
    list_res = client.get("/api/{{model.name.lower()}}s")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # Test get by id
    get_res = client.get(f"/api/{{model.name.lower()}}s/{created_id}")
    assert get_res.status_code == 200

    # Test delete (soft delete)
    del_res = client.delete(f"/api/{{model.name.lower()}}s/{created_id}")
    assert del_res.status_code == 200
""")
        }

    def generate(self, spec: AppSpec) -> Dict[str, str]:
        files = {}
        files["backend/tests/conftest.py"] = self.templates["conftest"].render()
        for model in spec.models:
            test_path = f"backend/tests/test_{model.name.lower()}s.py"
            files[test_path] = self.templates["model_test"].render(model=model)
        return files

    def write(self, spec: AppSpec, base_path: str) -> str:
        files = self.generate(spec)
        output = Path(base_path)

        for filename, content in files.items():
            target = output / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content.strip(), encoding="utf-8")

        return str(output)
