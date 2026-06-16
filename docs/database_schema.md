# Database Schema

## users

- `id`
- `name`
- `email`
- `password_hash`
- `role`
- `blocked`
- `email_verified`
- `profile_picture`
- `created_at`

## sessions

- `token`
- `user_id`
- `created_at`

## reset_tokens

- `token`
- `user_id`
- `used`
- `created_at`

## predictions

- `id`
- `user_id`
- `news_text`
- `source_url`
- `label`
- `confidence`
- `fake_probability`
- `real_probability`
- `source_score`
- `risk_level`
- `processing_time_ms`
- `model_used`
- `explanation`
- `saved`
- `created_at`

## datasets

- `id`
- `title`
- `label`
- `sample_text`
- `created_at`

## activity_logs

- `id`
- `user_id`
- `action`
- `details`
- `created_at`
