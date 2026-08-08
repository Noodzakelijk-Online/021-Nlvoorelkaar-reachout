# Task Graph and Stabilization Gates

```mermaid
flowchart TD
    A[Repository and secret audit] --> B[Fail-closed runtime]
    B --> C[Schema and state invariants]
    C --> D[Local critical path]
    D --> E[Review and safety controls]
    E --> F[Backup, recovery, diagnostics]
    F --> G[Tests and adversarial checks]
    G --> H[Documentation and traceability]
    H --> I[History scrub]
    I --> J[Fresh-clone verification]
    J --> K[Push and CI]
    K --> L[Owner provider acceptance]
```

Gates A-K are repository work. Gate L remains blocked by credential rotation, provider permission, private account access, and manual operator evidence. A failed gate stops release claims but does not erase completed local work.

