# Technical Debt and Maintenance Plan

| Priority | Item | Exit condition |
| --- | --- | --- |
| Release gate | Rotate/revoke historical Google credentials | New private client/token; activity reviewed; old material invalid. |
| Release gate | Validate current NLvoorelkaar integration and terms | Owner-approved account test and written permission decision. |
| High | Desktop accessibility and high-DPI evidence | Keyboard, screen-reader, focus, contrast, and scaling checklist passes. |
| High | Signed Windows distribution | Reproducible clean-machine build, signing, install/uninstall, rollback proof. |
| Medium | Large-dataset performance baseline | Representative private fixture, documented limits, query/UI timing budget. |
| Medium | Internationalization | Extract UI strings and add reviewed Dutch/English catalogs if required. |
| Low | Remove compatibility modules | Confirm no downstream import consumers, then delete in a major release. |

Monthly maintenance: review Dependabot/CodeQL, run full tests and audits, verify a backup restore, inspect ambiguous attempts, and confirm provider terms. Before each release: fresh clone, supported Python matrix, network-free smoke, repository/history safety scan, changelog, and owner sign-off for any live provider change.

