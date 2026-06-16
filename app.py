from pathlib import Path
from urllib.parse import urlencode
from io import BytesIO, StringIO
import csv
import html
import json
import time

from flask import Flask, Response, jsonify, make_response, redirect, request, send_file

from app.auth import (
    SESSION_COOKIE,
    create_jwt,
    hash_password,
    new_reset_token,
    new_session_token,
    validate_email,
    verify_jwt,
    verify_password,
)
from app.detector import FakeNewsDetector
from app.storage import AppStore


BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "app" / "templates"
DATASET_PATH = BASE_DIR / "data" / "training_data.json"
DB_PATH = BASE_DIR / "data" / "predictions.db"

app = Flask(__name__, static_folder="app/static", static_url_path="/static")
detector = FakeNewsDetector(DATASET_PATH).train()
store = AppStore(DB_PATH)
RATE_LIMITS = {}


def ensure_admin_account():
    if not store.find_user_by_email("admin@example.com"):
        store.create_user("Admin User", "admin@example.com", hash_password("admin123"), "admin")


ensure_admin_account()


@app.before_request
def security_checks():
    if not rate_limit(request.remote_addr or "local"):
        return Response("Too many requests", status=429)
    if request.method == "POST" and not valid_post_origin():
        return Response("Invalid request origin", status=403)


def rate_limit(key):
    now = time.time()
    window = [stamp for stamp in RATE_LIMITS.get(key, []) if now - stamp < 60]
    if len(window) >= 120:
        RATE_LIMITS[key] = window
        return False
    window.append(now)
    RATE_LIMITS[key] = window
    return True


def valid_post_origin():
    origin = request.headers.get("Origin") or request.headers.get("Referer")
    if not origin:
        return True
    return request.host in origin


def current_user():
    return store.user_for_session(request.cookies.get(SESSION_COOKIE))


def current_api_user():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    claims = verify_jwt(auth_header.removeprefix("Bearer ").strip())
    return store.find_user_by_id(claims["sub"]) if claims else None


def require_user():
    user = current_user()
    if not user:
        return None, redirect("/login")
    if user.get("blocked"):
        return None, redirect("/logout")
    return user, None


def require_admin():
    user, response = require_user()
    if response:
        return None, response
    if user["role"] != "admin":
        return None, Response("Admin access required", status=403)
    return user, None


def template(name):
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def fill(raw, data):
    rendered = raw
    for key, value in data.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))
    return rendered


def notice(message):
    return f'<p class="notice">{message}</p>' if message else ""


def error(message):
    return f'<p class="auth-error">{html.escape(message)}</p>' if message else ""


def login_response(location, token=None, clear=False):
    response = make_response(redirect(location))
    if token:
        response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="Lax", path="/")
    if clear:
        response.set_cookie(SESSION_COOKIE, "", max_age=0, httponly=True, samesite="Lax", path="/")
    return response


def render_app(title, user, body):
    admin_nav = ""
    if user["role"] == "admin":
        admin_nav = (
            '<a href="/admin">Admin</a><a href="/admin/users">Users</a>'
            '<a href="/admin/reports">Reports</a><a href="/admin/datasets">Datasets</a>'
            '<a href="/admin/model">Model</a><a href="/admin/logs">Activity Logs</a>'
        )
    return fill(
        template("app_shell.html"),
        {
            "TITLE": title,
            "USER_NAME": html.escape(user["name"]),
            "USER_EMAIL": html.escape(user["email"]),
            "USER_ROLE": html.escape(user["role"]),
            "BODY": body,
            "ADMIN_NAV": admin_nav,
        },
    )


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)