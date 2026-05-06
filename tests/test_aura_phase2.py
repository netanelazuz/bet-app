"""Phase 2: Create bet, join bet (variable stake, creator cannot join), close bet, Aura redistribution."""
from datetime import datetime, timezone

from app import db
from app.models import User, Bet, BetStatus, Difficulty, Participation
from app.aura import redistribute_aura


def test_create_bet_requires_auth(client, init_db):
    r = client.get("/bets/create", follow_redirects=False)
    assert r.status_code in (302, 401)


def test_create_bet(client, init_db):
    client.post("/auth/register", json={"username": "alice", "password": "secret123"})
    login_resp = client.post("/auth/login", json={"username": "alice", "password": "secret123"})
    token = login_resp.get_json()["access_token"]
    r = client.post(
        "/bets/create",
        data={"topic": "Will it rain?", "difficulty": "easy"},
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    with client.application.app_context():
        bet = Bet.query.filter_by(topic="Will it rain?").first()
        assert bet is not None
        assert bet.status == BetStatus.OPEN
        assert bet.difficulty == Difficulty.EASY


def test_creator_cannot_join_own_bet(client, init_db):
    client.post("/auth/register", json={"username": "alice", "password": "secret123"})
    client.post("/auth/login", json={"username": "alice", "password": "secret123"})
    with client.application.app_context():
        u = User.query.filter_by(username="alice").first()
        u.aura = 50
        db.session.commit()
        bet = Bet(
            topic="My bet",
            description="",
            difficulty=Difficulty.MEDIUM,
            status=BetStatus.OPEN,
            created_by_id=u.id,
        )
        db.session.add(bet)
        db.session.commit()
        bet_id = bet.id
    # Try to join as creator (same user); auth via cookie from login above
    r = client.post(
        f"/bets/{bet_id}/join",
        data={"stake": "10", "side": "yes"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    with client.application.app_context():
        p = Participation.query.filter_by(bet_id=bet_id).first()
        assert p is None


def test_join_bet_deducts_aura(client, init_db):
    client.post("/auth/register", json={"username": "alice", "password": "secret123"})
    client.post("/auth/register", json={"username": "bob", "password": "secret123"})
    with client.application.app_context():
        alice = User.query.filter_by(username="alice").first()
        bob = User.query.filter_by(username="bob").first()
        alice.aura = 100
        bob.aura = 100
        db.session.commit()
        bet = Bet(
            topic="Rain",
            difficulty=Difficulty.MEDIUM,
            status=BetStatus.OPEN,
            created_by_id=alice.id,
        )
        db.session.add(bet)
        db.session.commit()
        bet_id = bet.id
    login_resp = client.post("/auth/login", json={"username": "bob", "password": "secret123"})
    token = login_resp.get_json()["access_token"]
    r = client.post(
        f"/bets/{bet_id}/join",
        data={"stake": "30", "side": "yes"},
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    with client.application.app_context():
        bob = User.query.filter_by(username="bob").first()
        assert bob.aura == 70
        p = Participation.query.filter_by(bet_id=bet_id, user_id=bob.id).first()
        assert p is not None
        assert p.stake == 30
        assert p.side == "yes"


def test_aura_redistribution(client, init_db):
    with client.application.app_context():
        alice = User(username="alice", password_hash="x", aura=100, open_bets=0)
        bob = User(username="bob", password_hash="x", aura=60, open_bets=1)   # already staked 40
        charlie = User(username="charlie", password_hash="x", aura=40, open_bets=1)  # already staked 60
        db.session.add_all([alice, bob, charlie])
        db.session.commit()
        bet = Bet(
            topic="X",
            difficulty=Difficulty.MEDIUM,
            status=BetStatus.OPEN,
            created_by_id=alice.id,
        )
        db.session.add(bet)
        db.session.commit()
        p1 = Participation(bet_id=bet.id, user_id=bob.id, stake=40, side="yes", is_winner=None)
        p2 = Participation(bet_id=bet.id, user_id=charlie.id, stake=60, side="no", is_winner=None)
        db.session.add_all([p1, p2])
        db.session.commit()
        bet.status = BetStatus.CLOSED
        bet.winning_side = "yes"
        bet.closed_at = datetime.now(timezone.utc)
        redistribute_aura(bet)
        db.session.commit()
        bob = db.session.get(User, bob.id)
        charlie = db.session.get(User, charlie.id)
        # Winner Bob: stake 40, gets stake back + (40/40)*60*1 = 40+60 = 100. aura 60+100 = 160.
        assert bob.aura == 160
        assert bob.wins == 1
        assert charlie.losses == 1
        assert charlie.aura == 40  # unchanged (already deducted when joined)


def test_logout_clears_cookie(client, init_db):
    client.post("/auth/register", json={"username": "user", "password": "pass1234"})
    # JSON login; auth sets cookie on success for both JSON and form
    r = client.post("/auth/login", json={"username": "user", "password": "pass1234"})
    assert r.status_code == 200
    assert "auth_token" in (r.headers.get("Set-Cookie") or "")
    r = client.get("/auth/logout", follow_redirects=False)
    assert r.status_code == 302
    # Cookie should be cleared (max-age=0 or expires in past)
    set_cookie = r.headers.get("Set-Cookie") or ""
    assert "auth_token" in set_cookie or "auth_token=;" in set_cookie
