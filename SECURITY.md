# Security

## Secrets

Do not commit OAuth client secrets, access tokens, refresh tokens, local databases, logs, or generated build output.

Google Drive integration reads credentials from:

- `NLVE_GOOGLE_CLIENT_SECRET_PATH`, or `data/google_credentials.json`
- `NLVE_GOOGLE_TOKEN_PATH`, or `data/google_token.json`

The committed Google OAuth client secret and refresh token that previously existed in this repository must be treated as compromised. Revoke the refresh token and rotate or delete the OAuth client in Google Cloud before using this project again.

## Local Data

Runtime data is stored under `data/` by default and is ignored by git. This data can contain volunteer profile data, contact history, message bodies, and OAuth tokens, so it should be backed up and deleted according to the operator's privacy obligations.

## Reporting

Report vulnerabilities privately to the repository owner. Include the affected file, reproduction steps, impact, and any suggested remediation.
