# 0005: Remove the standalone Sentinel FastAPI app

> Classification: Decision Record. Status: accepted.

**Context.** `sentinel/pipeline/app.py` also defined a second FastAPI application with unauthenticated `/ingest`
and `/analyze`, unused by the API, tests or documentation, and the only reader of `SENTINEL_*` settings.

**Decision.** Delete the app, keep the pipeline classes, and have the real API read the `SENTINEL_*` settings.

**Consequences.** One authenticated entry point. Anyone who ran the module directly must use the API.
