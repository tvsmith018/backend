# CORS Fix for Ngrok Frontend

Last reviewed: 2026-05-05

## Why the error happens

`django-cors-headers` does not support wildcard domains like `https://*.ngrok.app` inside `CORS_ALLOWED_ORIGINS`.

That setting only accepts exact origins such as:

- `https://bigchiefdev.ngrok.app`
- `http://localhost:3000`

For wildcard-style matching, use `CORS_ALLOWED_ORIGIN_REGEXES`.

## Recommended Heroku config

Set these config vars on Heroku:

```bash
CORS_ALLOWED_ORIGINS=["http://localhost:3000","https://bigchiefnewz.com","https://bigchiefdev.ngrok.app"]
CORS_ALLOWED_ORIGIN_REGEXES=["^https://.*\\.ngrok\\.app$"]
CSRF_TRUSTED_ORIGINS=["http://localhost:3000","https://bigchiefnewz.com","https://*.ngrok.app"]
```

## Important note

If you only use one ngrok URL at a time, the safest option is to put the exact URL in `CORS_ALLOWED_ORIGINS`.

The regex setting is useful when ngrok URLs change often.
