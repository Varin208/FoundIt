"""
auth.py - register / log in / log out.

Login state is kept in Flask's signed session cookie (HttpOnly, so
JavaScript can't read it). Passwords are stored only as salted hashes.

Endpoints (JSON in, JSON out; errors look like {"error": "message"}):
    POST /api/auth/signup   {name, email, password}  -> {user}
    POST /api/auth/login    {email, password}        -> {user}
    POST /api/auth/logout                            -> {ok: true}
    GET  /api/auth/me                                -> {user}  (401 if logged out)
"""
import re
from functools import wraps

from flask import Blueprint, current_app, jsonify, request, session
from sqlalchemy.exc import IntegrityError

from models import User, db

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def error(message, status):
    return jsonify(error=message), status


def current_user():
    """The logged-in User, or None. Later steps import this too."""
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def login_required(view):
    """Put under @route to return 401 unless someone is logged in."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return error("Please log in.", 401)
        return view(*args, **kwargs)

    return wrapper


def start_session(user):
    session.clear()  # drop anything left over from a previous login
    session["user_id"] = user.id
    session.permanent = True


@auth_bp.post("/signup")
def signup():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")
    domain = current_app.config["ALLOWED_EMAIL_DOMAIN"]

    if not name or len(name) > 120:
        return error("Please enter your full name.", 400)
    if not EMAIL_PATTERN.match(email):
        return error("Please enter a valid email address.", 400)
    if domain and not email.endswith(domain):
        return error(f"Please use your AUPP email address (ends with {domain}).", 400)
    if len(password) < 8:
        return error("Password must be at least 8 characters.", 400)
    if len(password) > 128:
        return error("Password is too long.", 400)

    if User.query.filter_by(email=email).first():
        return error("An account with this email already exists. Try logging in instead.", 409)

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:  # two sign-ups with the same email at the same moment
        db.session.rollback()
        return error("An account with this email already exists. Try logging in instead.", 409)

    start_session(user)
    return jsonify(user=user.to_public_dict()), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        # Same message for "no such email" and "wrong password" on purpose.
        return error("That email and password combination doesn't match our records.", 401)

    start_session(user)
    return jsonify(user=user.to_public_dict())


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@auth_bp.get("/me")
def me():
    user = current_user()
    if user is None:
        return error("Not logged in.", 401)
    return jsonify(user=user.to_public_dict())
