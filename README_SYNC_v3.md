# Synchronization Notes

`main_sync_enhanced.py` contains the enhanced synchronization entry point. It shares the same local security model as the main application:

- credentials and tokens stay outside version control
- local databases, exports, logs, and backups stay under ignored paths
- Google Drive support is optional and uses the configured OAuth client secret/token paths
- live synchronization should respect platform terms, rate limits, and privacy obligations

## Run

```bash
python main_sync_enhanced.py
```

Before running live sync, configure NLvoorelkaar credentials through the application flow and, if Google Drive backup is needed, provide Google OAuth files through:

```bash
set NLVE_GOOGLE_CLIENT_SECRET_PATH=C:\secure\google_credentials.json
set NLVE_GOOGLE_TOKEN_PATH=C:\secure\google_token.json
```

## Checks

```bash
python -m compileall -q .
python -m pytest -q
```

Avoid adding claims about private or hidden profile access unless they are backed by a reviewed, compliant integration.
