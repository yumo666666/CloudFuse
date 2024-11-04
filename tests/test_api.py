import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_admin_page():
    response = client.get("/admin/")
    assert response.status_code == 200

def test_function_call():
    response = client.get("/function/example_function")
    assert response.status_code == 200

def test_invalid_function():
    response = client.get("/function/nonexistent_function")
    assert response.status_code == 404 