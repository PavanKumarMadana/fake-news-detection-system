# API Documentation

Base URL:

```text
http://127.0.0.1:8000
```

## POST /api/login

Returns a JWT token for API access.

Request:

```json
{
  "email": "admin@example.com",
  "password": "admin123"
}
```

Response:

```json
{
  "token": "jwt-token",
  "token_type": "Bearer"
}
```

## POST /api/verify-news

Requires:

```text
Authorization: Bearer <token>
```

Request:

```json
{
  "news_text": "Shocking secret cure goes viral",
  "source_url": "https://example.com/article"
}
```

Response:

```json
{
  "result": {
    "label": "fake",
    "confidence": 99,
    "fake_probability": 99.1,
    "real_probability": 0.9,
    "source_score": 58,
    "source_summary": "Source domain requires manual cross-checking.",
    "signals": []
  }
}
```

## GET /api/history

Supports browser session authentication or JWT authentication.

Response:

```json
{
  "items": []
}
```

## Security

- Browser auth uses HttpOnly SameSite cookies.
- API auth uses HMAC-SHA256 JWT.
- Passwords use PBKDF2 hashing.
- Rate limiting is applied per client IP.
