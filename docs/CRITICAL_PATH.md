# Critical Path

## Outcome

An operator can intake reviewed candidates, prepare a campaign, review exact message snapshots, record assisted delivery evidence, classify a response, approve a follow-up, record an outcome, export data, and verify a backup without any provider network call.

## Steps and Invariants

1. **Candidate intake** imports reviewed CSV/JSON or, only after explicit opt-in and login, runs bounded live search.
2. **Campaign preparation** requires a name, target, and template before readiness passes.
3. **Draft creation** persists the rendered message. Approval applies to that exact snapshot.
4. **Delivery** is either manual with evidence or an explicit bounded live-send action. Draft claiming is atomic.
5. **Recovery** turns stale started sends into `external_outcome_unknown`; it never retries automatically.
6. **Responses and follow-ups** are persisted and separately approved before assisted delivery evidence.
7. **Outcome and privacy** preserve an audit trail and expose export, retention, archive, and redaction actions.
8. **Backup** succeeds only when the local archive passes verification. Drive upload is a separate opt-in action.

## Automated Proof

```powershell
python run.py smoke
```

Expected guarantees: `status=pass`, `network_used=false`, `external_messages_sent=0`, one exported record, a verified backup, and a healthy schema.

## Live Acceptance Boundary

Keep all live flags disabled until owner-approved provider acceptance is complete. A green local smoke test proves the local workflow; it does not prove current provider permission or page compatibility.

