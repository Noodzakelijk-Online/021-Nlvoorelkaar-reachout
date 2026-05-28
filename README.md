# NLvoorelkaar Reachout

Desktop tooling for managing NLvoorelkaar outreach workflows: volunteer search, local persistence, message queues, reminders, and optional Google Drive backup/export support.

This repository stores application code only. Runtime data, credentials, tokens, local databases, logs, backups, and packaged builds are intentionally ignored.

## Requirements

- Python 3.10, 3.11, or 3.12
- A virtual environment is recommended
- NLvoorelkaar account credentials for live use
- Optional Google Cloud OAuth client credentials for Google Drive export/backup

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

For development checks:

```bash
python -m pip install -r requirements-dev.txt
python -m compileall -q .
python -m pytest -q
```

## Google Drive Credentials

Google Drive support is optional. Do not commit OAuth client secrets or refresh tokens.

By default the application reads:

- OAuth client secret: `data/google_credentials.json`
- OAuth refresh token: `data/google_token.json`

You can override those locations:

```bash
set NLVE_GOOGLE_CLIENT_SECRET_PATH=C:\secure\google_credentials.json
set NLVE_GOOGLE_TOKEN_PATH=C:\secure\google_token.json
```

The application requests the narrower `drive.file` scope so it can work only with files it creates or files explicitly opened with the app.

## Local Data

The application stores operational data locally under ignored paths such as `data/`, `logs/`, and `backups/`. These files may contain personal data and should be handled according to your organization policy and applicable privacy law.

## Security Notes

- Never commit `credentials.json`, `token.json`, `client_secret*.json`, encrypted credential files, local databases, logs, backups, or `dist/` builds.
- If secrets were ever committed to a branch, remove them from the working tree, revoke the exposed credentials, rotate tokens, and rewrite repository history before treating the repository as clean.
- Use a strong master password for encrypted local credentials.
- Keep scraping and messaging rates conservative and compliant with NLvoorelkaar terms.

See [SECURITY.md](SECURITY.md) for the full security guidance.

## Testing

The current automated checks are:

```bash
python -m compileall -q .
python -m pytest -q
```

CI runs these checks on Python 3.10, 3.11, and 3.12 and also runs a dependency audit against `requirements.txt`.
