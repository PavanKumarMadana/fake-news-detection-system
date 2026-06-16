# Architecture Diagram

```text
Browser / API Client
        |
        v
Python HTTP Controller Layer
        |
        +-- Auth Service
        |      - Password hashing
        |      - Session cookies
        |      - JWT generation and validation
        |      - Reset tokens
        |
        +-- Verification Service
        |      - Fake news classifier
        |      - Confidence scoring
        |      - Explanation signals
        |      - Source credibility analysis
        |
        +-- Admin Service
               - User management
               - Dataset management
               - Model monitoring
               - Analytics
        |
        v
SQLite Database
        |
        +-- users
        +-- sessions
        +-- reset_tokens
        +-- predictions
        +-- datasets
```

## Clean Architecture Mapping

- `app.py`: Controllers and route handlers.
- `app/auth.py`: Security and authentication utilities.
- `app/detector.py`: AI engine and source credibility logic.
- `app/storage.py`: Persistence gateway for SQLite.
- `app/templates`: Presentation layer.
- `app/static`: UI theme and responsive SaaS styling.
