# Third-Party Notices

Runtime, development, build, and frontend dependencies are declared with exact versions in `requirements.txt`, `requirements-dev.txt`, `requirements-build.txt`, and `web/package-lock.json`. Their upstream licenses govern those packages; this repository does not relicense them. The Windows release script generates an environment-specific CycloneDX software bill of materials. Review it and include all notices required by the packaged dependency set before distribution.

External services are optional and separately governed:

- NLvoorelkaar: live use requires current platform permission and terms review.
- Google Drive API: optional app-scoped backup using the `drive.file` OAuth scope.

No source file grants permission to scrape, automate, or send contrary to a provider's current terms or applicable law.
