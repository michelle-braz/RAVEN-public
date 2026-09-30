# Future work

Improvements that can safely follow the first sales. None is needed to run RAVEN today.

* **Use approved resolutions in analysis.** They are recorded but do not yet influence later results.
* **Alerting.** A webhook channel exists as a building block; wire it with an https-only allow-list and retries.
* **Persistent recurrence.** Keep the recurrence window across restarts.
* **Per-user identity and audit trail** if customers need to know who did what (today: keys per integration).
* **Database storage** behind `api/beta/store.py` once a customer passes about 100,000 records.
* **Encryption at rest and key hashing** in the application, if customers cannot use volume encryption.
* **Calibration study** of the score on customer-approved data, and a published accuracy note.
* **Independent penetration test** and formal ASVS assessment.
* **Signed images and SBOM** published with each release.
* **Multi-tenant hosting** only if operating many instances becomes the bottleneck ([ADR-0001](docs/decisions/0001-single-tenant-self-hosted.md)).
