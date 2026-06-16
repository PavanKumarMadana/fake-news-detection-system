# Class Diagram

```text
FakeNewsRequestHandler
 |-- handles HTTP routes
 |-- validates authenticated and admin access
 |-- renders dashboard/admin/auth/report pages

AppStore
 |-- create_user()
 |-- user_for_session()
 |-- add_prediction()
 |-- search_predictions()
 |-- user_dashboard_stats()
 |-- analytics()
 |-- log_activity()

FakeNewsDetector
 |-- train()
 |-- predict()
 |-- source_credibility()
 |-- sentiment()
 |-- similar_news()

auth.py
 |-- hash_password()
 |-- verify_password()
 |-- create_jwt()
 |-- verify_jwt()
 |-- parse_cookies()
```
