from pathlib import Path
from urllib.parse import urlencode
from io import BytesIO, StringIO
import csv
import html
import json
import re
import time

from flask import Flask, Response, jsonify, make_response, redirect, request, send_file

from application.auth import (
    SESSION_COOKIE,
    create_jwt,
    hash_password,
    new_reset_token,
    new_session_token,
    validate_email,
    verify_jwt,
    verify_password,
)
from application.detector import FakeNewsDetector
from application.evidence import extract_claim_from_url
from application.storage import AppStore


BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "application" / "templates"
DATASET_PATH = BASE_DIR / "data" / "training_data.json"
DB_PATH = BASE_DIR / "data" / "predictions.db"

app = Flask(__name__, static_folder="application/static", static_url_path="/static")
detector = FakeNewsDetector(DATASET_PATH).train()
store = AppStore(DB_PATH)
RATE_LIMITS = {}
URL_ONLY_RE = re.compile(r"^(https?://|www\.)\S+$", re.IGNORECASE)


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


def verify_form(action, label, placeholder, button, url_mode=False):
    if url_mode:
        field = f'<label>{label}</label><input name="source_url" placeholder="{placeholder}" required>'
        hidden = '<input type="hidden" name="news_text" value="">'
    else:
        field = (
            f'<label>{label}</label><textarea name="news_text" placeholder="{placeholder}" required></textarea>'
            '<label>Source URL (optional)</label><input name="source_url" placeholder="https://trusted-source.com/article">'
        )
        hidden = ""
    return f"""
    <section class="panel analyzer-panel">
        <span class="eyebrow">AI verification engine</span>
        <h2>{button}</h2>
        <form method="post" action="{action}" class="stack-form loading-form">
            {field}{hidden}
            <button type="submit">{button}</button>
        </form>
    </section>
    """


def dashboard_overview(user_id):
    stats, monthly = store.user_dashboard_stats(user_id)
    recent = store.recent_predictions(user_id, 6)
    total = stats.get("total") or 0
    fake_count = stats.get("fake_count") or 0
    real_count = stats.get("real_count") or 0
    accuracy = stats.get("accuracy") or 0
    last = stats.get("last_verification") or "No verifications yet"
    fake_percent = round((fake_count / total) * 100) if total else 0
    cards = "".join(
        f"<article><span>{label}</span><strong>{value}</strong></article>"
        for label, value in [
            ("Total Verifications", total),
            ("Fake News Count", fake_count),
            ("Real News Count", real_count),
            ("Accuracy Percentage", f"{accuracy}%"),
            ("Recent Activities", len(recent)),
            ("Last Verification Date", last),
        ]
    )
    bars = "".join(
        f'<div class="bar-row"><span>{row["month"]}</span><div><i style="width:{min(row["total"] * 18, 100)}%"></i></div><b>{row["total"]}</b></div>'
        for row in reversed(monthly)
    ) or '<div class="empty-state">No monthly data yet.</div>'
    return f"""
    <section class="metrics user-stats">{cards}</section>
    <section class="chart-grid">
        <article class="panel chart-card"><span class="eyebrow">Fake vs Real</span><h2>Prediction Split</h2>
        <div class="pie-chart" style="--fake-percent:{fake_percent}%"><span>{fake_percent}% fake</span></div></article>
        <article class="panel chart-card"><span class="eyebrow">Monthly analysis</span><h2>Verification Volume</h2>
        <div class="bar-chart">{bars}</div></article>
    </section>
    """


def result_panel(result, prediction_id=None):
    if not result:
        return """
        <section class="panel result-empty">
            <span class="status-icon">?</span><span class="eyebrow">Ready</span>
            <h2>Submit news content to view AI analysis.</h2>
            <p>Results include fake/real probability, confidence score, explanation, and source credibility.</p>
        </section>
        """
    badge = "unknown" if result["label"] == "unknown" else ("fake" if result["label"] == "fake" else "real")
    status_mark = "!" if badge == "fake" else ("?" if badge == "unknown" else "OK")
    signals = "".join(f"<li>{html.escape(signal)}</li>" for signal in result["signals"])
    keywords = "".join(f'<span>{html.escape(word)}</span>' for word in result.get("keyword_analysis", []))
    save = (
        f'<form method="post" action="/reports/save"><input type="hidden" name="prediction_id" value="{prediction_id}">'
        '<button type="submit" class="secondary">Save Report</button></form>'
        if prediction_id
        else ""
    )
    return f"""
    <section class="panel result-active">
        <span class="status-icon {badge}">{status_mark}</span>
        <span class="eyebrow">Prediction result</span>
        <div class="prediction-line"><h2 class="{badge}">{result["label"].title()} News</h2><strong>{result["confidence"]}% confidence</strong></div>
        <p class="risk-line">Risk Level: <b>{result["risk_level"]}</b></p>
        <div class="meter"><span style="width:{result["fake_probability"]}%"></span></div>
        <div class="score-grid">
            <p><b>{result["fake_probability"]}%</b><span>Fake Probability</span></p>
            <p><b>{result["real_probability"]}%</b><span>Real Probability</span></p>
            <p><b>{result["source_score"]}</b><span>Source Score</span></p>
            <p><b>{result["processing_time_ms"]}ms</b><span>Processing Time</span></p>
            <p><b>{result["model_used"]}</b><span>Model Used</span></p>
            <p><b>{result["prediction_date"]}</b><span>Prediction Date</span></p>
        </div>
        <h3>Reasons</h3><ul class="signals">{signals}</ul>
        <h3>Keyword Analysis</h3><div class="keyword-row">{keywords}</div>
        <p><b>Sentiment:</b> {html.escape(result.get("sentiment", "Neutral"))}</p>{save}
    </section>
    """


def history_table(rows, title, compact=False, page=1, total=0, per_page=8, search="", label="", sort="desc"):
    body = ""
    for row in rows:
        query = urlencode({"id": row["id"]})
        delete_form = (
            f'<form method="post" action="/reports/delete" class="inline-form">'
            f'<input type="hidden" name="prediction_id" value="{row["id"]}">'
            '<button type="submit" class="secondary">Delete</button></form>'
        )
        body += f"""
        <tr><td>{html.escape(row["news_text"][:90])}</td><td>{html.escape(row["source_url"] or "-")}</td>
        <td><span class="pill {row["label"]}">{row["label"].title()}</span></td><td>{row["confidence"]}%</td>
        <td>{row["source_score"]}</td><td>{row["created_at"]}</td><td><a class="mini-link" href="/report?{query}">View Details</a>{delete_form}</td></tr>
        """
    if not body:
        body = '<tr><td colspan="7"><div class="empty-state">No records found.</div></td></tr>'
    pager = ""
    if not compact and total > per_page:
        base = {"q": search, "label": label, "sort": sort}
        pager = (
            f'<div class="pager"><a class="mini-link" href="/history?{urlencode({**base, "page": max(page - 1, 1)})}">Previous</a>'
            f"<span>Page {page}</span>"
            f'<a class="mini-link" href="/history?{urlencode({**base, "page": page + 1})}">Next</a></div>'
        )
    return f"""
    <section class="panel"><span class="eyebrow">Records</span><h2>{title}</h2>
    <div class="table-wrap"><table><thead><tr><th>News Text</th><th>URL</th><th>Result</th><th>Confidence</th><th>Source</th><th>Time</th><th>Details</th></tr></thead><tbody>{body}</tbody></table></div>{pager}</section>
    """


def history_filters(search, label, sort):
    return f"""
    <section class="panel filter-panel"><form method="get" action="/history" class="filter-form">
        <input name="q" value="{html.escape(search)}" placeholder="Search news, URL, explanation">
        <select name="label"><option value="">All</option><option value="fake" {"selected" if label == "fake" else ""}>Fake</option><option value="real" {"selected" if label == "real" else ""}>Real</option></select>
        <select name="sort"><option value="desc" {"selected" if sort == "desc" else ""}>Newest First</option><option value="asc" {"selected" if sort == "asc" else ""}>Oldest First</option></select>
        <button type="submit">Apply</button><a class="mini-link" href="/export/csv">Export CSV</a>
    </form></section>
    """


def report_detail(report):
    explanation = "".join(f"<li>{html.escape(line)}</li>" for line in (report["explanation"] or "").splitlines() if line)
    delete_form = (
        f'<form method="post" action="/reports/delete" class="inline-form">'
        f'<input type="hidden" name="prediction_id" value="{report["id"]}">'
        '<button type="submit" class="secondary">Delete Report</button></form>'
    )
    return f"""
    <section class="panel report-detail"><span class="eyebrow">Detailed report</span><h2>{report["label"].title()} News</h2>
    <div class="score-grid">
        <p><b>{report["confidence"]}%</b><span>Confidence</span></p><p><b>{report["source_score"]}</b><span>Source Score</span></p>
        <p><b>{html.escape(report.get("risk_level") or "-")}</b><span>Risk Level</span></p><p><b>{report.get("processing_time_ms") or 0}ms</b><span>Processing Time</span></p>
        <p><b>{html.escape(report.get("model_used") or "-")}</b><span>Model Used</span></p><p><b>{report["created_at"]}</b><span>Timestamp</span></p>
    </div><h3>Full Article</h3><pre class="article-box">{html.escape(report["news_text"])}</pre>
    <h3>Explanation</h3><ul class="signals">{explanation}</ul>
    <div class="report-actions"><a class="mini-link" href="/export/pdf?id={report["id"]}">Export PDF</a><a class="mini-link" href="/export/csv">Export CSV</a>{delete_form}</div></section>
    """


def build_prediction_input(news_text, source_url):
    news_text = (news_text or "").strip()
    source_url = (source_url or "").strip()
    if news_text and not source_url and URL_ONLY_RE.match(news_text):
        source_url = news_text
        news_text = ""
    if source_url and not news_text:
        extracted = extract_claim_from_url(source_url)
        extracted_text = extracted.get("text", "").strip()
        if extracted_text:
            return extracted_text[:5000], source_url
        return f"News article from {source_url}", source_url
    return news_text, source_url


def simple_pdf(text):
    safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    lines = safe.splitlines()[:45]
    stream = "BT /F1 11 Tf 50 780 Td " + " T* ".join(f"({line[:95]}) Tj" for line in lines) + " ET"
    objects = [
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj",
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
        f"5 0 obj << /Length {len(stream.encode('latin-1', 'ignore'))} >> stream\n{stream}\nendstream endobj",
    ]
    pdf = "%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf.encode("latin-1")))
        pdf += obj + "\n"
    xref = len(pdf.encode("latin-1"))
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n"
    pdf += f"trailer << /Root 1 0 R /Size {len(objects) + 1} >>\nstartxref\n{xref}\n%%EOF"
    return pdf.encode("latin-1", "ignore")


@app.get("/")
@app.get("/dashboard")
def dashboard():
    user, response = require_user()
    if response:
        return response
    recent = store.recent_predictions(user["id"], 6)
    body = (
        dashboard_overview(user["id"])
        + verify_form("/predict", "News headline or article text", "Paste a claim, headline, or article body...", "Analyze News")
        + result_panel(None)
        + history_table(recent, "Recent Activities", compact=True)
    )
    return render_app("Dashboard", user, body)


@app.get("/verify-url")
def verify_url_page():
    user, response = require_user()
    if response:
        return response
    body = verify_form("/verify-url", "Article URL", "https://example.com/news/article", "Verify URL", True) + result_panel(None)
    return render_app("Verify URL", user, body)


@app.get("/history")
def history_page():
    user, response = require_user()
    if response:
        return response
    search = request.args.get("q", "")
    label = request.args.get("label", "")
    sort = request.args.get("sort", "desc")
    page = max(int(request.args.get("page", "1") or 1), 1)
    per_page = 8
    rows = store.search_predictions(user["id"], per_page, (page - 1) * per_page, search, label, sort)
    total = store.count_predictions(user["id"], search, label)
    return render_app("Verification History", user, history_filters(search, label, sort) + history_table(rows, "Verification History", False, page, total, per_page, search, label, sort))


@app.get("/saved-reports")
def saved_reports():
    user, response = require_user()
    if response:
        return response
    return render_app("Saved Reports", user, history_table(store.recent_predictions(user["id"], 50, True), "Saved Reports"))


@app.get("/report")
def report_page():
    user, response = require_user()
    if response:
        return response
    prediction_id = int(request.args.get("id", "0"))
    report = store.prediction_detail(user["id"], prediction_id)
    if not report and user["role"] == "admin":
        report = store.admin_prediction_detail(prediction_id)
    if not report:
        return Response("Report not found", status=404)
    return render_app("Report Details", user, report_detail(report))


@app.post("/predict")
@app.post("/verify-url")
def predict_news():
    user, response = require_user()
    if response:
        return response
    news_text, source_url = build_prediction_input(
        request.form.get("news_text", ""),
        request.form.get("source_url", ""),
    )
    if len(news_text) > 5000 or len(source_url) > 500:
        return Response("Input too large", status=400)
    result = detector.predict(news_text, source_url)
    prediction_id = store.add_prediction(user["id"], news_text, result, source_url)
    store.log_activity(user["id"], "verification_complete", f"{result['label']} / {result['confidence']}%")
    body = verify_form("/predict", "News headline or article text", html.escape(news_text), "Analyze News") + result_panel(result, prediction_id) + history_table(store.recent_predictions(user["id"], 10), "Verification History")
    return render_app("Verification Result", user, body)


@app.post("/reports/save")
def save_report():
    user, response = require_user()
    if response:
        return response
    store.save_report(user["id"], int(request.form.get("prediction_id", "0")))
    return redirect("/saved-reports")


@app.post("/reports/delete")
def delete_report():
    user, response = require_user()
    if response:
        return response
    prediction_id = int(request.form.get("prediction_id", "0"))
    deleted = store.delete_user_report(user["id"], prediction_id)
    if deleted:
        store.log_activity(user["id"], "report_deleted", f"prediction_id={prediction_id}")
    return redirect(request.headers.get("Referer") or "/history")


@app.get("/login")
@app.get("/signup")
def auth_page():
    if current_user():
        return redirect("/")
    mode = "signup" if request.path == "/signup" else "login"
    is_signup = mode == "signup"
    return fill(
        template("auth.html"),
        {
            "MODE": mode,
            "TITLE": "Create account" if is_signup else "Welcome back",
            "SUBTITLE": "Create your workspace to start verifying news." if is_signup else "Login to continue to your dashboard.",
            "NAME_FIELD_CLASS": "" if is_signup else "hidden",
            "PRIMARY_ACTION": "Create Account" if is_signup else "Login",
            "SWITCH_TEXT": "Already have an account?" if is_signup else "New user?",
            "SWITCH_URL": "/login" if is_signup else "/signup",
            "SWITCH_ACTION": "Login" if is_signup else "Create account",
            "FORGOT_BLOCK": "" if is_signup else '<a href="/forgot-password">Forgot password?</a>',
            "ERROR_BLOCK": "",
            "NAME_VALUE": "",
            "EMAIL_VALUE": "",
        },
    )


def auth_page_with_error(mode, message, values):
    is_signup = mode == "signup"
    return fill(
        template("auth.html"),
        {
            "MODE": mode,
            "TITLE": "Create account" if is_signup else "Welcome back",
            "SUBTITLE": "Create your workspace to start verifying news." if is_signup else "Login to continue to your dashboard.",
            "NAME_FIELD_CLASS": "" if is_signup else "hidden",
            "PRIMARY_ACTION": "Create Account" if is_signup else "Login",
            "SWITCH_TEXT": "Already have an account?" if is_signup else "New user?",
            "SWITCH_URL": "/login" if is_signup else "/signup",
            "SWITCH_ACTION": "Login" if is_signup else "Create account",
            "FORGOT_BLOCK": "" if is_signup else '<a href="/forgot-password">Forgot password?</a>',
            "ERROR_BLOCK": error(message),
            "NAME_VALUE": html.escape(values.get("name", "")),
            "EMAIL_VALUE": html.escape(values.get("email", "")),
        },
    )


@app.post("/login")
def login():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    user = store.find_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        return auth_page_with_error("login", "Invalid email or password.", {"email": email})
    if user.get("blocked"):
        return auth_page_with_error("login", "This account is blocked.", {"email": email})
    token = new_session_token()
    store.create_session(token, user["id"])
    return login_response("/", token)


@app.post("/signup")
def signup():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    if len(name) < 2 or not validate_email(email) or len(password) < 6:
        return auth_page_with_error("signup", "Enter valid signup details.", {"name": name, "email": email})
    role = "admin" if not store.list_users() else "user"
    user_id = store.create_user(name, email, hash_password(password), role)
    if not user_id:
        return auth_page_with_error("signup", "Email already registered.", {"name": name, "email": email})
    token = new_session_token()
    store.create_session(token, user_id)
    return login_response("/", token)


@app.get("/logout")
def logout():
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        store.delete_session(token)
    return login_response("/login", clear=True)


@app.get("/forgot-password")
def forgot_page():
    return fill(template("forgot.html"), {"MESSAGE": ""})


@app.post("/forgot-password")
def forgot_password():
    email = request.form.get("email", "").strip()
    user = store.find_user_by_email(email)
    reset_link = ""
    if user:
        token = new_reset_token()
        store.create_reset_token(token, user["id"])
        reset_link = f' <a class="reset-link" href="/reset-password?token={token}">Open reset link</a>'
    return fill(template("forgot.html"), {"MESSAGE": notice("If the account exists, a reset link is generated below for this local demo." + reset_link)})


@app.get("/reset-password")
def reset_page():
    return fill(template("reset.html"), {"TOKEN": html.escape(request.args.get("token", "")), "MESSAGE": ""})


@app.post("/reset-password")
def reset_password():
    token = request.form.get("token", "")
    password = request.form.get("password", "")
    record = store.consume_reset_token(token)
    if not record or len(password) < 6:
        return fill(template("reset.html"), {"TOKEN": html.escape(token), "MESSAGE": notice("Reset link invalid or password too short.")})
    store.update_password(record["user_id"], hash_password(password))
    return redirect("/login")


@app.get("/profile")
def profile_page(message=""):
    user, response = require_user()
    if response:
        return response
    body = f"""
    <section class="panel narrow"><span class="eyebrow">User profile</span><h2>Account Settings</h2>{notice(message)}
    <form method="post" action="/profile" class="stack-form"><label>Name</label><input name="name" value="{html.escape(user["name"])}" required>
    <label>Email</label><input name="email" type="email" value="{html.escape(user["email"])}" required>
    <label>Profile picture URL</label><input name="profile_picture" value="{html.escape(user.get("profile_picture") or "")}">
    <button type="submit">Update Profile</button></form><hr class="soft-line"><h2>Change Password</h2>
    <form method="post" action="/profile/password" class="stack-form"><label>Current password</label><input name="current_password" type="password" required>
    <label>New password</label><input name="new_password" type="password" required><div class="password-strength">Use 8+ characters with letters and numbers.</div>
    <button type="submit">Change Password</button></form></section>
    """
    return render_app("Profile", user, body)


@app.post("/profile")
def update_profile():
    user, response = require_user()
    if response:
        return response
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    if len(name) < 2 or not validate_email(email):
        return profile_page("Please enter valid profile details.")
    store.update_user(user["id"], name, email, request.form.get("profile_picture", "").strip())
    return profile_page("Profile updated successfully.")


@app.post("/profile/password")
def change_password():
    user, response = require_user()
    if response:
        return response
    account = store.find_user_by_email(user["email"])
    new_password = request.form.get("new_password", "")
    if not verify_password(request.form.get("current_password", ""), account["password_hash"]):
        return profile_page("Current password is incorrect.")
    if len(new_password) < 8 or not any(ch.isdigit() for ch in new_password):
        return profile_page("New password must be at least 8 characters and include a number.")
    store.update_password(user["id"], hash_password(new_password))
    return profile_page("Password changed successfully.")


@app.get("/admin")
@app.get("/admin/analytics")
def admin_dashboard():
    user, response = require_admin()
    if response:
        return response
    counts, recent = store.analytics()
    cards = "".join(f"<article><span>{label}</span><strong>{value}</strong></article>" for label, value in [("Users", counts["users"]), ("Verifications", counts["predictions"]), ("Fake Flags", counts["fake_count"]), ("Real Flags", counts["real_count"]), ("Dataset Samples", counts["datasets"])])
    rows = "".join(f"<tr><td>{r['label'].title()}</td><td>{r['confidence']}%</td><td>{r['source_score']}</td><td>{r['created_at']}</td></tr>" for r in recent) or '<tr><td colspan="4">No model events yet.</td></tr>'
    body = f'<section class="metrics dashboard-metrics">{cards}</section><section class="panel"><span class="eyebrow">Model monitoring</span><h2>Recent Predictions</h2><div class="table-wrap"><table><thead><tr><th>Label</th><th>Confidence</th><th>Source Score</th><th>Time</th></tr></thead><tbody>{rows}</tbody></table></div></section>'
    return render_app("Admin Analytics", user, body)


@app.get("/admin/users")
def admin_users():
    user, response = require_admin()
    if response:
        return response
    rows = ""
    for item in store.list_users():
        rows += f"""
        <tr><td>{html.escape(item["name"])}</td><td>{html.escape(item["email"])}</td><td><span class="pill">{html.escape(item["role"])}</span></td>
        <td><span class="pill {'fake' if item['blocked'] else 'real'}">{'Blocked' if item['blocked'] else 'Active'}</span></td>
        <td><form method="post" action="/admin/users/role" class="inline-form"><input type="hidden" name="user_id" value="{item["id"]}">
        <select name="role"><option value="user" {'selected' if item["role"] == "user" else ''}>user</option><option value="admin" {'selected' if item["role"] == "admin" else ''}>admin</option></select><button>Update</button></form>
        <form method="post" action="/admin/users/block" class="inline-form"><input type="hidden" name="user_id" value="{item["id"]}"><input type="hidden" name="blocked" value="{0 if item["blocked"] else 1}"><button class="secondary">{'Unblock' if item["blocked"] else 'Block'}</button></form></td></tr>
        """
    return render_app("User Management", user, f'<section class="panel"><span class="eyebrow">Role based access</span><h2>User Management</h2><div class="table-wrap"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Action</th></tr></thead><tbody>{rows}</tbody></table></div></section>')


@app.post("/admin/users/role")
def admin_role():
    user, response = require_admin()
    if response:
        return response
    store.update_role(int(request.form.get("user_id", "0")), request.form.get("role", "user"))
    return redirect("/admin/users")


@app.post("/admin/users/block")
def admin_block():
    user, response = require_admin()
    if response:
        return response
    store.set_user_blocked(int(request.form.get("user_id", "0")), int(request.form.get("blocked", "0")))
    return redirect("/admin/users")


@app.get("/admin/reports")
def admin_reports():
    user, response = require_admin()
    if response:
        return response
    rows = "".join(f'<tr><td>{html.escape(r["name"])}</td><td>{html.escape(r["news_text"][:80])}</td><td><span class="pill {r["label"]}">{r["label"].title()}</span></td><td>{r["confidence"]}%</td><td>{r["created_at"]}</td><td><a class="mini-link" href="/report?id={r["id"]}">View</a><form method="post" action="/admin/reports/delete" class="inline-form"><input type="hidden" name="report_id" value="{r["id"]}"><button class="secondary">Delete</button></form></td></tr>' for r in store.list_all_reports()) or '<tr><td colspan="6">No reports found.</td></tr>'
    return render_app("Reports", user, f'<section class="panel"><span class="eyebrow">Reports</span><h2>All Verification Reports</h2><div class="table-wrap"><table><thead><tr><th>User</th><th>News</th><th>Prediction</th><th>Confidence</th><th>Time</th><th>Action</th></tr></thead><tbody>{rows}</tbody></table></div></section>')


@app.post("/admin/reports/delete")
def admin_delete_report():
    user, response = require_admin()
    if response:
        return response
    store.delete_report(int(request.form.get("report_id", "0")))
    return redirect("/admin/reports")


@app.get("/admin/datasets")
def admin_datasets():
    user, response = require_admin()
    if response:
        return response
    rows = "".join(f"<tr><td>{html.escape(r['title'])}</td><td>{html.escape(r['label'])}</td><td>{html.escape(r['sample_text'][:90])}</td></tr>" for r in store.list_dataset_samples()) or '<tr><td colspan="3">No dataset samples added.</td></tr>'
    body = f'<section class="panel"><span class="eyebrow">Dataset management</span><h2>Add Dataset Sample</h2><form method="post" action="/admin/datasets" class="dataset-form"><input name="title" placeholder="Dataset title" required><select name="label"><option value="fake">fake</option><option value="real">real</option></select><textarea name="sample_text" placeholder="Training sample text" required></textarea><button>Add Sample</button></form></section><section class="panel"><h2>Dataset Records</h2><div class="table-wrap"><table><thead><tr><th>Title</th><th>Label</th><th>Text</th></tr></thead><tbody>{rows}</tbody></table></div></section>'
    return render_app("Dataset Management", user, body)


@app.post("/admin/datasets")
def admin_add_dataset():
    user, response = require_admin()
    if response:
        return response
    store.add_dataset_sample(request.form.get("title", "Untitled")[:120], request.form.get("label", "fake"), request.form.get("sample_text", "")[:2000])
    return redirect("/admin/datasets")


@app.get("/admin/model")
def admin_model():
    user, response = require_admin()
    if response:
        return response
    counts, _ = store.analytics()
    body = f'<section class="panel"><span class="eyebrow">Model monitoring</span><h2>AI Engine Status</h2><div class="monitor-grid"><article><span>Algorithm</span><strong>Multinomial Naive Bayes</strong></article><article><span>Vocabulary Size</span><strong>{len(detector.vocabulary)}</strong></article><article><span>Training Samples</span><strong>{sum(detector.class_doc_counts.values())}</strong></article><article><span>Total Predictions</span><strong>{counts["predictions"]}</strong></article></div></section>'
    return render_app("Model Monitoring", user, body)


@app.get("/admin/logs")
def admin_logs():
    user, response = require_admin()
    if response:
        return response
    rows = "".join(f"<tr><td>{html.escape(r.get('name') or 'System')}</td><td>{html.escape(r['action'])}</td><td>{html.escape(r['details'] or '')}</td><td>{r['created_at']}</td></tr>" for r in store.list_activity_logs()) or '<tr><td colspan="4">No activity logs yet.</td></tr>'
    return render_app("Activity Logs", user, f'<section class="panel"><span class="eyebrow">Audit trail</span><h2>Activity Logs</h2><div class="table-wrap"><table><thead><tr><th>User</th><th>Action</th><th>Details</th><th>Time</th></tr></thead><tbody>{rows}</tbody></table></div></section>')


@app.get("/export/csv")
def export_csv():
    user, response = require_user()
    if response:
        return response
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "prediction", "confidence", "source_score", "timestamp", "source_url", "news_text"])
    for row in store.search_predictions(user["id"], limit=1000):
        writer.writerow([row["id"], row["label"], row["confidence"], row["source_score"], row["created_at"], row["source_url"], row["news_text"]])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=verification-history.csv"})


@app.get("/export/pdf")
def export_pdf():
    user, response = require_user()
    if response:
        return response
    report = store.prediction_detail(user["id"], int(request.args.get("id", "0")))
    if not report:
        return Response("Report not found", status=404)
    content = f"Fake News Detecting System Report\n\nUser: {report['user_name']} <{report['user_email']}>\nPrediction: {report['label'].title()}\nConfidence: {report['confidence']}%\nSource Score: {report['source_score']}\nTimestamp: {report['created_at']}\n\nNews Content:\n{report['news_text']}\n\nExplanation:\n{report['explanation']}\n"
    return send_file(BytesIO(simple_pdf(content)), mimetype="application/pdf", as_attachment=True, download_name=f"report-{report['id']}.pdf")


@app.get("/help")
@app.get("/faq")
@app.get("/contact")
@app.get("/about")
def static_pages():
    user, response = require_user()
    if response:
        return response
    title = {"help": "Help Center", "faq": "FAQ", "contact": "Contact Us", "about": "About Project"}[request.path.strip("/")]
    body = f'<section class="panel"><span class="eyebrow">Support</span><h2>{title}</h2><div class="empty-state"><p>Use this page for project guidance, FAQs, contact information, and project overview.</p></div></section>'
    return render_app(title, user, body)


@app.post("/api/login")
def api_login():
    payload = request.get_json(silent=True) or {}
    user = store.find_user_by_email(payload.get("email", ""))
    if not user or not verify_password(payload.get("password", ""), user["password_hash"]):
        return jsonify({"error": "Invalid credentials"}), 401
    return jsonify({"token": create_jwt({"sub": user["id"], "role": user["role"], "email": user["email"]}), "token_type": "Bearer"})


@app.post("/api/verify-news")
def api_verify_news():
    user = current_api_user()
    if not user:
        return jsonify({"error": "Invalid JWT"}), 401
    payload = request.get_json(silent=True) or {}
    news_text, source_url = build_prediction_input(payload.get("news_text", ""), payload.get("source_url", ""))
    return jsonify({"result": detector.predict(news_text, source_url), "news_text": news_text, "source_url": source_url})


@app.get("/api/history")
def api_history():
    user = current_user() or current_api_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401
    return jsonify({"items": store.recent_predictions(user["id"])})


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)

