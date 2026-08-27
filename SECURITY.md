# Security policy

## Reporting

Please use GitHub's private security-advisory flow for vulnerabilities that could expose user data, execute unintended input, weaken the foreground-only macro boundary, or permit untrusted combat data to affect the host system. Avoid posting sensitive logs or exploit details in a public issue.

## Supported code

Security fixes target the latest `main` branch. Research probes are version-scoped and are not guaranteed to remain compatible after a game update.

## Data handling

The project should not collect account identifiers, nicknames, platform IDs, credentials, or network payloads. Diagnostic submissions must be minimized and redacted. Local JSON-line transport is treated as untrusted input and must be bounded, validated, and session-scoped before it reaches the UI.

Cataloged third-party tools are also untrusted. They must never auto-run or inherit the combat bridge's read-only claim. A managed copy requires an exact catalog size and SHA-256, and removal is limited to the exact toolbox-owned leaf. Do not submit or commit third-party executables unless their redistribution permission is documented.
