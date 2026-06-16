# ER Diagram

```text
USERS
-----
id PK
name
email UNIQUE
password_hash
role
created_at

SESSIONS
--------
token PK
user_id FK -> users.id
created_at

RESET_TOKENS
------------
token PK
user_id FK -> users.id
used
created_at

PREDICTIONS
-----------
id PK
user_id FK -> users.id
news_text
source_url
label
confidence
fake_probability
real_probability
source_score
explanation
saved
created_at

DATASETS
--------
id PK
title
label
sample_text
created_at
```

## Relationships

- One user can have many sessions.
- One user can have many reset tokens.
- One user can have many prediction records.
- Saved reports are prediction records with `saved = 1`.
- Dataset samples are managed by admins and used as training references.
