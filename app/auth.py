"""JWT authentication and registration."""
import re
from functools import wraps
from flask import Blueprint, request, jsonify, render_template, g, redirect, make_response
import base64
import hmac
import hashlib
import json
import bcrypt

# Prefer PyJWT; fallback to stdlib-only JWT for compatibility
def _jwt_encode(payload, secret, algorithm="HS256"):
    try:
        from jwt import encode as _encode
        token = _encode(payload, secret, algorithm=algorithm)
        return token if isinstance(token, str) else token.decode("utf-8")
    except (ImportError, AttributeError):
        pass
    # Minimal HS256 JWT (header.payload.signature)
    header = {"alg": "HS256", "typ": "JWT"}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=").decode()
    header_b64 = base64.urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode()).rstrip(b"=").decode()
    msg = f"{header_b64}.{payload_b64}".encode()
    sig = base64.urlsafe_b64encode(hmac.new(secret.encode(), msg, hashlib.sha256).digest()).rstrip(b"=").decode()
    return f"{header_b64}.{payload_b64}.{sig}"


def _jwt_decode(token, secret, algorithms=None):
    try:
        from jwt import decode as _decode
        return _decode(token, secret, algorithms=algorithms or ["HS256"])
    except (ImportError, AttributeError):
        pass
    import time
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token")
    payload_b64 = parts[1]
    payload_b64 += "=" * (4 - len(payload_b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    if payload.get("exp") and payload["exp"] < time.time():
        raise ValueError("Token expired")
    msg = f"{parts[0]}.{parts[1]}".encode()
    expected_sig = base64.urlsafe_b64encode(hmac.new(secret.encode(), msg, hashlib.sha256).digest()).rstrip(b"=").decode()
    if not hmac.compare_digest(parts[2], expected_sig):
        raise ValueError("Invalid signature")
    return payload
from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__)

# Cookie name and max age for browser auth
AUTH_COOKIE = "auth_token"
AUTH_COOKIE_MAX_AGE = 3600 * 24 * 7  # 7 days


def _get_jwt_secret():
    from flask import current_app
    return current_app.config.get("JWT_SECRET_KEY") or current_app.config["SECRET_KEY"]


def _get_jwt_expires():
    from flask import current_app
    return current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", 3600)


def create_access_token(identity):
    import time
    now = int(time.time())
    payload = {
        # PyJWT expects sub to be a string by spec; cast explicitly.
        "sub": str(identity),
        "exp": now + _get_jwt_expires(),
        "iat": now,
    }
    return _jwt_encode(payload, _get_jwt_secret(), "HS256")


def decode_token(token):
    if not token:
        return None
    try:
        payload = _jwt_decode(token, _get_jwt_secret(), ["HS256"])
        return payload.get("sub")
    except Exception:
        return None


def get_current_user_id():
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if not token:
        token = request.cookies.get("auth_token") or request.form.get("access_token") or request.args.get("access_token")
    return decode_token(token)


def login_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        user_id = get_current_user_id()
        if not user_id:
            if request.accept_mimetypes.best == "application/json":
                return jsonify({"error": "Authentication required"}), 401
            return redirect(f"/auth/login?next={request.url}")
        g.current_user_id = int(user_id)
        return f(*args, **kwargs)
    return inner


def _validate_username(s: str) -> bool:
    if not s or len(s) < 2 or len(s) > 80:
        return False
    return bool(re.match(r"^[a-zA-Z0-9_-]+$", s))


def _validate_password(s: str) -> bool:
    if not s or len(s) < 6:
        return False
    return True


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    data = request.get_json(silent=True) or request.form or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    nickname = (data.get("nickname") or "").strip() or username
    bio = (data.get("bio") or "").strip()[:500]

    if not _validate_username(username):
        return jsonify({"error": "Invalid username"}), 400
    if not _validate_password(password):
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken"}), 409

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=12)
    ).decode("utf-8")
    user = User(
        username=username,
        password_hash=password_hash,
        nickname=nickname,
        bio=bio,
        aura=1000,
    )
    db.session.add(user)
    db.session.commit()
    token = create_access_token(user.id)
    if request.content_type and "application/json" not in request.content_type:
        resp = make_response(redirect("/dashboard"))
        resp.set_cookie(AUTH_COOKIE, token, max_age=AUTH_COOKIE_MAX_AGE, httponly=True, samesite="Lax")
        return resp
    return jsonify({"access_token": token, "user": user.to_dict()}), 201


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    data = request.get_json(silent=True) or request.form or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    user = User.query.filter_by(username=username).first()
    if not user or not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
        return jsonify({"error": "Invalid credentials"}), 401
    token = create_access_token(user.id)
    wants_json = request.content_type and "application/json" in (request.content_type or "")
    if wants_json:
        resp = make_response(jsonify({"access_token": token, "user": user.to_dict()}))
    else:
        resp = make_response(redirect("/dashboard"))
    resp.set_cookie(AUTH_COOKIE, token, max_age=AUTH_COOKIE_MAX_AGE, httponly=True, samesite="Lax")
    return resp


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    resp = redirect(request.args.get("next") or "/")
    resp.delete_cookie(AUTH_COOKIE)
    return resp
