# Synthetic log examples

Every file in this directory was written specifically for the public repository. The examples do not reproduce third-party logs, customer environments, internal identifiers, IP addresses, URLs, tokens, or real incident narratives.

- `clear-incident.txt` contains several signals consistent with a service outage after a synthetic configuration change.
- `normal-operation.txt` contains healthy application activity.
- `ambiguous-signal.txt` contains a transient warning with incomplete evidence.

Each line is standalone JSON and can be copied into the `message` field of `POST /v1/analyze` as plain text. The examples are intentionally compact: RAVEN currently analyzes one signal per API request.

