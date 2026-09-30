# Security policy

## Reporting a vulnerability

Report privately through GitHub's private vulnerability reporting for this repository (Security tab → *Report a
vulnerability*). Do not open a public issue for a vulnerability, and do not include real incident data, credentials
or personal data in a report; a minimal synthetic reproduction is enough.

Response and disclosure commitments are set in customer agreements ([legal](docs/legal/README.md)).

## Scope and posture

The security model, controls and known residual risks are in [docs/security](docs/security/security-model.md).
RAVEN has not been independently audited.

## Never commit

`.env` files, API keys, real incident payloads, logs, tickets or transcripts, JSONL data files, backups, or personal
data. `.gitignore` covers the usual paths and a test scans tracked files for secret patterns.
