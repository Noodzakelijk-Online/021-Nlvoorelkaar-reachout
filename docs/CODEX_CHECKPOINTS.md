# Resume Checkpoints

## Baseline

- Repository: `Noodzakelijk-Online/021-Nlvoorelkaar-reachout`
- Branch: `main`
- Starting commit: `7f2da80`
- Maintained runtime: Python 3.10-3.12 desktop application

## Release Invariants

- No tracked credentials, tokens, databases, logs, backups, or `dist/` artifacts.
- All provider flags default off and are rejected in test mode.
- No external send without persisted exact-snapshot approval and explicit action.
- No automatic retry after an ambiguous external outcome.
- No Drive auth/write during construction.
- No restore without a verified rollback backup.
- Local critical-path smoke uses no network and sends no external message.

## Resume Procedure

Run `git status`, `python scripts/check_repository_safety.py --history`, `python -m pytest -q`, `python run.py smoke`, and `git ls-remote origin refs/heads/main`. Read `TODO.md` before enabling any live provider feature.

