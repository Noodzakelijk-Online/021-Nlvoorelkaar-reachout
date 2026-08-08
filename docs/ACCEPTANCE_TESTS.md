# Acceptance Tests

| ID | Scenario | Automated evidence | Manual evidence |
| --- | --- | --- | --- |
| A01 | Fresh local configuration fails closed | Runtime tests and `doctor` | Confirm Operations shows all live features disabled. |
| A02 | Reviewed CSV/JSON candidate intake | Import unit/integration tests | Import owner-approved sample and inspect fields. |
| A03 | Local campaign through outcome | `python run.py smoke` | Walk through the same UI path. |
| A04 | Unapproved or modified draft cannot send | Ledger tests | Attempt send before approval and after snapshot change. |
| A05 | Duplicate concurrent send is rejected | Atomic claim test | Not required. |
| A06 | Stale in-flight send is not retried | Reconciliation test | Compare provider history before re-approval. |
| A07 | Batch and daily caps fail closed | Runtime/ledger tests | Inspect error and unchanged state. |
| A08 | Safety stop blocks provider action | Controller/runtime tests | Activate stop while idle and while a task is active. |
| A09 | Backup excludes secrets and verifies | Backup/privacy tests | Restore into a disposable directory and inspect records. |
| A10 | Malicious archive is rejected | Traversal/symlink/expansion tests | Not required. |
| A11 | Support bundle contains no personal records | Bundle test | Open ZIP and review both files before sharing. |
| A12 | Drive constructor has no side effects | Unit test | Instantiate with network disconnected. |
| A13 | Live NLvoorelkaar search/send | Not automatable without approved account | Blocked pending terms/account/selector acceptance. |
| A14 | Google OAuth upload/readback/restore | Not automatable without private rotated credentials | Blocked pending credential rotation. |
| A15 | Keyboard, screen reader, high DPI | No reliable desktop automation in this repository | Required on supported Windows machines. |
| A16 | Signed clean-machine install | No signing certificate/build target | Required only for binary distribution. |

Tests must not use real provider credentials or report provider success from mocks. Test doubles are limited to deterministic isolation and assert state changes or failures.

