# Operator Runbook

## Start and Diagnose

Use Python 3.10-3.12, install `requirements.txt`, then run `python run.py doctor`. Warnings for absent provider credentials are expected for local-only use. Database or configuration failures are not.

Run the network-free release smoke test with `python run.py smoke` before using real records.

## Normal Workflow

Use Candidate Intake, Campaigns, Messages, Responses, Follow-ups, Privacy, and Operations in that order. Approve only an exact message you have read. For assisted delivery, record evidence only after confirming the provider accepted the message.

## Enable a Provider

1. Confirm current provider terms and owner permission.
2. Set only the needed `NLVE_*_ENABLED=1` flag.
3. Keep search pages, send batch, and daily limits conservative.
4. Log in through the application; do not put credentials in source or `.env` files committed to Git.
5. Run one owner-approved test record and inspect the audit/send history before expanding.

Drive additionally requires newly rotated private OAuth credentials. Use the Operations action so local backup verification occurs before upload.

## Emergency Stop

Activate **Operations > Safety Stop**. It blocks new provider actions and asks active tasks to cancel. It cannot retract a request already accepted by a provider.

If a send has no confirmed result, run:

```powershell
python run.py reconcile-sends --minutes 15
```

Then inspect provider history. Do not retry until the external outcome is known.

## Backup and Recovery

Create and verify a backup before maintenance: `python run.py backup --name before-maintenance`. Restore only from a verified local archive. Restore first creates a rollback backup and aborts if that protection cannot be created.

## Incident Response

Disable all live flags, activate Safety Stop, preserve the database and audit log, create a privacy-safe support bundle, and rotate affected provider credentials. Never attach raw logs, databases, tokens, or message exports to a public issue.

