# 0002: Keep append-only JSONL storage

> Classification: Decision Record. Status: accepted.

**Context.** Volume is low, records are immutable, and backup by file copy is simple. A database adds a service to
run, secure, back up and upgrade. Risks found in the existing store: interleaved writes, world-readable files, one
torn line breaking reads.

**Decision.** Keep JSONL. Write each record with one `O_APPEND` write, `fsync` decisions, restrict permissions,
skip unreadable lines, and provide export, retention and erasure tooling. Measured: summary endpoints read the whole
file (0.7 s at 100,000 records).

**Consequences.** No transactions or indexes; fine to about 100,000 records per file. Beyond that, purge or migrate
to a database behind `api/beta/store.py`, the only module that touches the files.
