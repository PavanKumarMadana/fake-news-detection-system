# Fake News Detecting System

A Python-based fake news detection project inspired by the structure of the provided MCA project reference PDF. It includes a browser UI, a simple machine-learning style Naive Bayes classifier, SQLite prediction history, sample training data, tests, and report documentation.

## Features

- Paste a news headline or article and detect whether it is likely fake or real.
- Register, login, and logout with session-based authentication.
- Forgot password and reset password flow.
- JWT authentication for secure APIs.
- Role based access with admin and user workspaces.
- User dashboard with news verification, URL verification, history, saved reports, and profile.
- Admin dashboard with user management, dataset management, model monitoring, and analytics.
- Passwords are stored using PBKDF2 hashing, not plain text.
- Shows confidence score, fake probability, real probability, and explanation signals.
- Includes source credibility analysis and user-wise SQLite records.
- Dashboard statistics, pie chart, monthly bar chart, recent activity, and last verification date.
- Search, filter, sort, pagination, View Details, CSV export, and PDF report export.
- Help Center, FAQ, Contact Us, and About Project pages.
- Admin report management, block/unblock users, and activity logs.
- Includes responsive SaaS dashboard styling and dark mode.
- Runs without Flask, Django, pandas, or scikit-learn.
- Includes a project report draft in `docs/project_report.md`.

## Run

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:8000/login
```

Create a new account from the register page, then login to use the dashboard.

Default admin account:

```text
Email: admin@example.com
Password: admin123
```

## Test

```powershell
python -m unittest discover tests
```

## Project Structure

```text
Fake_News_Detection_System/
  app.py
  app/
    auth.py
    detector.py
    storage.py
    templates/app_shell.html
    templates/auth.html
    templates/forgot.html
    templates/index.html
    templates/reset.html
    static/styles.css
  data/
    training_data.json
  docs/
    api.md
    architecture.md
    class_diagram.md
    database_schema.md
    er_diagram.md
    project_report.md
    use_case_diagram.md
  tests/
    test_detector.py
```

## Note

This is an academic/demo implementation. For production-level fake news detection, use a large verified dataset, stronger NLP models, source reputation checks, and human fact-checking workflows.
