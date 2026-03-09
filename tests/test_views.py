"""Tests for dashboard, profile, leaderboard."""
import pytest


def test_leaderboard_public(client, init_db):
    r = client.get("/leaderboard")
    assert r.status_code == 200


def test_dashboard_requires_auth(client, init_db):
    r = client.get("/dashboard", follow_redirects=False)
    assert r.status_code in (302, 401)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json().get("status") == "ok"
