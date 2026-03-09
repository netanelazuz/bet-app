"""Tests for auth: register, login, validation."""
import pytest


def test_register_json(client, init_db):
    r = client.post(
        "/auth/register",
        json={"username": "alice", "password": "secret123", "nickname": "Alice"},
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 201
    data = r.get_json()
    assert "access_token" in data
    assert data["user"]["username"] == "alice"
    assert data["user"]["nickname"] == "Alice"
    assert "password_hash" not in str(data)


def test_register_validation_username(client, init_db):
    r = client.post("/auth/register", json={"username": "a", "password": "secret12"})
    assert r.status_code == 400
    r = client.post("/auth/register", json={"username": "validuser", "password": "short"})
    assert r.status_code == 400


def test_login_success(client, init_db):
    client.post("/auth/register", json={"username": "bob", "password": "pass1234"})
    r = client.post("/auth/login", json={"username": "bob", "password": "pass1234"})
    assert r.status_code == 200
    assert "access_token" in r.get_json()


def test_login_invalid(client, init_db):
    r = client.post("/auth/login", json={"username": "nobody", "password": "wrong"})
    assert r.status_code == 401
