# Remaining External and Release Work

Implemented repository work is tracked in `docs/GOAL_COMPLETION_MATRIX.md`. The following items cannot be completed from source code alone:

- Revoke the historically exposed Google refresh token.
- Delete or rotate the historically exposed Google OAuth client secret.
- Review Google account and Drive activity for misuse.
- Confirm current NLvoorelkaar terms and obtain any required platform approval for live search or sending.
- Run a controlled acceptance test against the current NLvoorelkaar login, search, message, and confirmation pages with an owner-approved test account.
- Run a controlled Google Drive OAuth, upload, readback, and restore test with newly rotated private credentials.
- Complete keyboard/screen-reader and high-DPI manual UI review on supported Windows versions.
- Produce and verify a signed Windows build on a clean machine if binary distribution is required.

Live flags must remain disabled until their corresponding provider acceptance work is complete.
