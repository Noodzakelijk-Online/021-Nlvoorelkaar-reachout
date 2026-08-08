# UI Action Audit

| Surface | Read actions | State-changing actions | Guard |
| --- | --- | --- | --- |
| Dashboard | Counts, next actions, activity | Navigate only | Truthful zero/unknown states. |
| Candidate Intake | Runtime readiness, selected file | Import; bounded live search | File validation; live flag, login, page cap. |
| Campaigns | Campaigns, readiness, summary | Create, draft, send approved | Required fields; final send confirmation; caps. |
| Messages | Draft snapshot/status | Edit, approve, reject, copy, confirm manual send | Sent/in-flight immutable; reason/evidence required. |
| Responses | Response queue | Record/classify response | Persisted source and audit. |
| Follow-ups | Due queue | Approve, reject, confirm assisted send | Separate review and evidence. |
| Privacy | Retention/export/redaction state | Export, archive, redact | Explicit selection/action and audit. |
| Operations | Runtime/provider/database/task status | Safety stop, clear, backup, Drive upload, reconcile | Confirm destructive/external actions; verified local backup first. |

All visible commands resolve to maintained callbacks. Unknown views and retired provider automation fail closed. The sidebar scrolls so controls remain reachable at the supported minimum window size.

