import base64
import hashlib
import hmac
import json
import secrets
import time


SESSION_COOKIE = "fake_news_session"
JWT_SECRET = "change-this-secret-before-deployment"


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        140_000,
    ).hex()
    return f"{salt}${password_hash}"


def verify_password(password, stored_hash):
    try:
        salt, expected_hash = stored_hash.split("$", 1)
    except ValueError:
        return False
    candidate_hash = hash_password(password, salt).split("$", 1)[1]
    return hmac.compare_digest(candidate_hash, expected_hash)


def new_session_token():
    return secrets.token_urlsafe(32)


def new_reset_token():
    return secrets.token_urlsafe(24)


def parse_cookies(header):
    cookies = {}
    if not header:
        return cookies
    for item in header.split(";"):
        if "=" not in item:
            continue
        key, value = item.strip().split("=", 1)
        cookies[key] = value
    return cookies


def b64url_encode(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def b64url_decode(value):
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_jwt(payload, expires_in=3600):
    header = {"alg": "HS256", "typ": "JWT"}
    claims = dict(payload)
    claims["exp"] = int(time.time()) + expires_in
    head = b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    body = b64url_encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(JWT_SECRET.encode("utf-8"), f"{head}.{body}".encode("ascii"), hashlib.sha256).digest()
    return f"{head}.{body}.{b64url_encode(signature)}"


def verify_jwt(token):
    try:
        head, body, signature = token.split(".")
        expected = hmac.new(JWT_SECRET.encode("utf-8"), f"{head}.{body}".encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(b64url_decode(signature), expected):
            return None
        claims = json.loads(b64url_decode(body))
        if claims.get("exp", 0) < int(time.time()):
            return None
        return claims
    except Exception:
        return None


def validate_email(email):
    return "@" in email and "." in email and len(email) <= 120


def validate_password(password):
    return len(password) >= 6
