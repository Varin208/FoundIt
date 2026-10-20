"""
app.py - FoundIt Flask server.

One server does both jobs:
  * serves the existing frontend files from ../frontend  (http://localhost:5000/login.html)
  * serves the JSON API under /api/...

Because the pages and the API share one address, the login cookie "just works"
and no CORS setup is needed.

Run it (from the backend folder):   python app.py
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

# Reads backend/.env (secrets live there, never in the code).
load_dotenv(BASE_DIR / ".env")

from auth import auth_bp  # noqa: E402  (imported after load_dotenv on purpose)
from models import db  # noqa: E402
from reports import reports_bp  # noqa: E402

DEV_SECRET_KEY = "dev-only-secret-change-me"


def create_app(test_config=None):
    app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")

    domain = os.environ.get("ALLOWED_EMAIL_DOMAIN", "@aupp.edu.kh").strip().lower()
    if domain and not domain.startswith("@"):
        domain = "@" + domain

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or DEV_SECRET_KEY,
        ALLOWED_EMAIL_DOMAIN=domain,
        SQLALCHEMY_DATABASE_URI="sqlite:///foundit.db",  # -> backend/instance/foundit.db
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        UPLOAD_DIR=str(BASE_DIR / "uploads"),
        MAX_CONTENT_LENGTH=11 * 1024 * 1024,  # photos up to ~10MB (plus form text)
    )
    if test_config:
        app.config.update(test_config)

    if app.config["SECRET_KEY"] == DEV_SECRET_KEY:
        print("WARNING: using the built-in dev SECRET_KEY. Set SECRET_KEY in backend/.env.")

    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)

    db.init_app(app)
    with app.app_context():
        db.create_all()  # creates any missing tables

    app.register_blueprint(auth_bp)
    app.register_blueprint(reports_bp)

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.errorhandler(413)
    def too_large(err):
        return jsonify(error="That photo is too large. Please use one under 10MB."), 413

    @app.errorhandler(404)
    def not_found(err):
        if request.path.startswith("/api/"):
            return jsonify(error="Not found."), 404
        return err

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
