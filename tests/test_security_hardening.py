"""Protects the commercial security promises: auth, limits, headers, fail-closed config."""
from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

import raven.api.auth as auth
import raven.api.main as main
from raven.api.beta_keys import BETA_REGISTRY
from raven.api.settings import ConfigError, Settings, load_settings

MASTER = "m" * 40
CUSTOMER = "customer-key-" + "c" * 20
BODY = {"message": "Checkout API returned HTTP 503 after a configuration change", "source": "application"}


@pytest.fixture
def keyed(monkeypatch):
    monkeypatch.setattr(auth, "_master_key", MASTER)
    monkeypatch.setattr(auth, "PRO_KEYS", frozenset({MASTER, CUSTOMER}))
    monkeypatch.setattr(auth, "FREE_KEYS", frozenset())
    monkeypatch.setattr(main, "_BETA_MASTER", MASTER)


def client_for(**env) -> TestClient:
    base = {"ENVIRONMENT": "development", **env}
    return TestClient(main.create_app(load_settings(base)))


# ── Authentication ────────────────────────────────────────────────────────────

def test_key_comparison_is_constant_time_api(keyed):
    assert auth.key_matches(CUSTOMER, [MASTER, CUSTOMER])
    assert not auth.key_matches(CUSTOMER[:-1], [MASTER, CUSTOMER])
    assert not auth.key_matches("ключ-не-ascii", [MASTER])  # non-ASCII must not raise


def test_missing_and_wrong_keys_are_rejected(keyed):
    with client_for() as c:
        assert c.post("/v1/analyze", json=BODY).status_code == 401
        wrong = c.post("/v1/analyze", json=BODY, headers={"X-API-Key": "nope"})
        assert wrong.status_code == 403
        assert wrong.json()["code"] == "invalid_api_key"
        assert c.post("/v1/analyze", json=BODY, headers={"X-API-Key": CUSTOMER}).status_code == 200


def test_brute_force_is_throttled_then_recovers(keyed):
    with client_for() as c:
        for _ in range(auth.AUTH_FAILURE_LIMIT):
            assert c.get("/beta/impact-summary", headers={"X-API-Key": "guess"}).status_code == 403
        blocked = c.get("/beta/impact-summary", headers={"X-API-Key": CUSTOMER})
        assert blocked.status_code == 429  # even a valid key waits: the address is locked out
        assert blocked.headers["Retry-After"] == "60"
        auth.reset_limiters()
        assert c.get("/beta/impact-summary", headers={"X-API-Key": CUSTOMER}).status_code == 200


def test_operator_endpoints_reject_customer_keys(keyed):
    with client_for() as c:
        for path in ("/ops/metrics", "/beta/business-proof"):
            assert c.get(path, headers={"X-API-Key": CUSTOMER}).status_code == 403
            assert c.get(path, headers={"X-API-Key": MASTER}).status_code == 200


def test_beta_endpoints_require_a_key(keyed):
    with client_for() as c:
        for method, path in (("get", "/beta/impact-summary"), ("post", "/beta/decision-impact"),
                             ("post", "/beta/validate-resolution"), ("post", "/evaluate")):
            assert getattr(c, method)(path).status_code == 401, path


def test_malformed_beta_key_registry_fails_loudly(monkeypatch):
    from raven.api import beta_keys
    monkeypatch.setenv("BETA_KEYS_JSON", "{not json")
    with pytest.raises(ConfigError):
        beta_keys._load_registry_from_env()
    monkeypatch.setenv("BETA_KEYS_JSON", '{"k": {"name": "x", "status": "maybe", "created_at": "t"}}')
    with pytest.raises(ConfigError):
        beta_keys._load_registry_from_env()


def test_revoked_beta_key_is_rejected(keyed, monkeypatch):
    key = "raven_beta_" + "a" * 16
    monkeypatch.setitem(BETA_REGISTRY, key, {"name": "x", "status": "active", "created_at": "t"})
    with client_for() as c:
        assert c.post("/v1/analyze", json=BODY, headers={"X-API-Key": key}).status_code == 200
        BETA_REGISTRY[key]["status"] = "revoked"
        auth.reset_limiters()
        assert c.post("/v1/analyze", json=BODY, headers={"X-API-Key": key}).status_code == 403


# ── Proxy-aware client address ────────────────────────────────────────────────

def test_forwarded_header_is_ignored_unless_proxy_is_trusted(keyed):
    with client_for() as c:  # 0 hops: spoofing X-Forwarded-For must not evade the lockout
        for i in range(auth.AUTH_FAILURE_LIMIT):
            c.get("/beta/impact-summary", headers={"X-API-Key": "g", "X-Forwarded-For": f"1.1.1.{i}"})
        r = c.get("/beta/impact-summary", headers={"X-API-Key": "g", "X-Forwarded-For": "9.9.9.9"})
        assert r.status_code == 429


def test_trusted_proxy_uses_the_rightmost_hop(keyed):
    with client_for(RAVEN_TRUSTED_PROXY_HOPS="1") as c:
        for _ in range(auth.AUTH_FAILURE_LIMIT):
            c.get("/beta/impact-summary", headers={"X-API-Key": "g", "X-Forwarded-For": "spoofed, 2.2.2.2"})
        # a different real client is unaffected
        ok = c.get("/beta/impact-summary", headers={"X-API-Key": CUSTOMER, "X-Forwarded-For": "3.3.3.3"})
        assert ok.status_code == 200
        blocked = c.get("/beta/impact-summary", headers={"X-API-Key": CUSTOMER, "X-Forwarded-For": "x, 2.2.2.2"})
        assert blocked.status_code == 429


def test_analyze_rate_limit_is_per_client_and_configurable(keyed):
    with client_for(RAVEN_RATE_LIMIT_PER_MINUTE="3") as c:
        codes = [c.post("/v1/analyze", json=BODY, headers={"X-API-Key": CUSTOMER}).status_code for _ in range(5)]
        assert codes == [200, 200, 200, 429, 429]
    with client_for() as c:  # default stays 30/min
        auth.reset_limiters()
        codes = [c.post("/v1/analyze", json=BODY, headers={"X-API-Key": CUSTOMER}).status_code for _ in range(31)]
        assert codes[:30] == [200] * 30 and codes[30] == 429
    with pytest.raises(ConfigError):
        load_settings({"RAVEN_RATE_LIMIT_PER_MINUTE": "many"})


# ── Input limits and validation ───────────────────────────────────────────────

def test_oversized_body_is_refused_before_parsing(keyed):
    with client_for(RAVEN_MAX_BODY_BYTES="2048") as c:
        r = c.post("/evaluate", content=b"{" + b" " * 5000 + b"}",
                   headers={"X-API-Key": CUSTOMER, "Content-Type": "application/json"})
        assert r.status_code == 413 and r.json()["code"] == "payload_too_large"


def test_authentication_happens_before_the_body_is_read(keyed):
    with client_for(RAVEN_MAX_BODY_BYTES="2048") as c:
        body = b"{" + b" " * 5000 + b"}"
        anon = c.post("/evaluate", content=body, headers={"Content-Type": "application/json"})
        assert anon.status_code == 401  # not 413: unauthenticated callers never get the body examined
        surrogate = c.post("/evaluate", content=b'{"message": "\\ud83d"}', headers={"Content-Type": "application/json"})
        assert surrogate.status_code == 401


def test_chunked_body_without_length_is_refused(keyed):
    with client_for() as c:
        def gen():
            yield b'{"message": "x"}'
        r = c.post("/evaluate", content=gen(), headers={"X-API-Key": CUSTOMER})
        assert r.status_code == 411


@pytest.mark.parametrize("payload", [
    [1, 2, 3], "text", 5, {"attempts": "abc"}, {"attempts": -1}, {"attempts": 10**12},
    {"attempts": True}, {"source": ["x"]}, {"user_id": {"a": 1}}, {"ip": "x" * 100}, {"message": 5},
])
def test_evaluate_rejects_bad_input_without_a_500(keyed, payload):
    with client_for() as c:
        r = c.post("/evaluate", json=payload, headers={"X-API-Key": CUSTOMER})
        assert r.status_code == 422, r.text
        assert r.json()["code"] == "validation_error" or "error" in r.json()


def test_evaluate_still_scores_valid_events(keyed):
    with client_for() as c:
        r = c.post("/evaluate", headers={"X-API-Key": CUSTOMER},
                   json={"action": "login_failed", "attempts": 5, "ip": "192.168.1.1", "source": "application"})
        assert r.status_code == 200 and r.json()["risk_score"] == 80 and r.json()["level"] == "HIGH"


def test_nul_and_lone_surrogates_do_not_crash_any_endpoint(keyed):
    """JSON escapes can smuggle characters no UTF-8 encoder accepts; none may cause a 500."""
    odd = "fail\\u0000ed \\ud83d login"  # raw JSON escapes: NUL and a lone surrogate
    hdr = {"X-API-Key": CUSTOMER, "Content-Type": "application/json"}
    feedback = ('{"incident_id": "i", "request_id": "r", "decision_taken": "ACCEPT", "action_taken": "%s",'
                ' "confidence": 3, "replaced_manual_process": false, "time_saved_minutes": 0,'
                ' "resolution_text": "%s", "memory_write_approved": true, "validated_by": "%s"}') % (odd, odd, odd)
    with client_for() as c:
        for path, raw in (
            ("/v1/analyze", '{"message": "%s", "source": "application"}' % odd),
            ("/evaluate", '{"message": "%s", "action": "%s"}' % (odd, odd)),
            ("/beta/decision-impact", feedback),
            ("/beta/validate-resolution", feedback),
        ):
            r = c.post(path, content=raw.encode(), headers=hdr)
            assert r.status_code < 500, (path, r.status_code, r.text)


# ── Headers, CORS, docs ───────────────────────────────────────────────────────

def test_security_headers_on_api_and_pages(keyed):
    with client_for() as c:
        api = c.post("/v1/analyze", json=BODY, headers={"X-API-Key": CUSTOMER})
        assert api.headers["x-content-type-options"] == "nosniff"
        assert api.headers["cache-control"] == "no-store"
        assert "frame-ancestors 'none'" in api.headers["content-security-policy"]
        assert api.headers["x-request-id"]
        assert api.headers["x-frame-options"] == "DENY"
        page = c.get("/")
        assert "unsafe-inline" not in page.headers["content-security-policy"]
        assert "frame-ancestors 'none'" in c.get("/missions/").headers["content-security-policy"]


def test_request_id_is_propagated_only_when_well_formed(keyed):
    with client_for() as c:
        assert c.get("/health", headers={"X-Request-ID": "abcdefgh-1234"}).headers["x-request-id"] == "abcdefgh-1234"
        forged = c.get("/health", headers={"X-Request-ID": "bad id\r\nX: y"})
        assert forged.headers["x-request-id"] != "bad id"


def test_cors_defaults_closed_in_production_and_is_explicit(keyed):
    prod = load_settings({"ENVIRONMENT": "production"})
    assert prod.cors_origins == () and prod.docs_enabled is False
    with client_for(CORS_ORIGINS="https://app.example.com") as c:
        ok = c.options("/v1/analyze", headers={"Origin": "https://app.example.com",
                                               "Access-Control-Request-Method": "POST"})
        assert ok.headers.get("access-control-allow-origin") == "https://app.example.com"
        bad = c.options("/v1/analyze", headers={"Origin": "https://evil.example",
                                                "Access-Control-Request-Method": "POST"})
        assert "access-control-allow-origin" not in bad.headers


def test_docs_are_off_in_production_and_on_in_development(keyed, monkeypatch, tmp_path):
    monkeypatch.setattr(auth, "_master_key", MASTER)
    settings = Settings(environment="production", docs_enabled=False, data_dir=tmp_path)
    (tmp_path).mkdir(exist_ok=True)
    with TestClient(main.create_app(settings)) as c:
        assert c.get("/docs").status_code == 404 and c.get("/openapi.json").status_code == 404
        assert c.get("/health").headers["strict-transport-security"].startswith("max-age=")
    with client_for() as c:
        assert c.get("/docs").status_code == 200


# ── Fail-closed production configuration ──────────────────────────────────────

def _prod(tmp_path, **kw):
    tmp_path.mkdir(exist_ok=True)
    return Settings(environment="production", data_dir=tmp_path, **kw)


@pytest.mark.parametrize("master,others,cors,fragment", [
    (None, frozenset(), (), "RAVEN_API_KEY must be set"),
    ("short", frozenset(), (), "at least 32"),
    (MASTER, frozenset({"tiny"}), (), "at least 24"),
    (MASTER, frozenset(), ("*",), "not '*'"),
])
def test_production_refuses_unsafe_configuration(tmp_path, master, others, cors, fragment):
    problems = _prod(tmp_path, cors_origins=cors).validate(master_key=master, other_keys=others)
    assert any(fragment in p for p in problems), problems


def test_production_refuses_to_start_and_names_every_problem(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "_master_key", None)
    monkeypatch.setattr(auth, "PRO_KEYS", frozenset())
    with pytest.raises(ConfigError, match="RAVEN_API_KEY must be set"):
        with TestClient(main.create_app(_prod(tmp_path))):
            pass


def test_production_starts_with_a_safe_configuration(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "_master_key", MASTER)
    monkeypatch.setattr(auth, "PRO_KEYS", frozenset({MASTER}))
    with TestClient(main.create_app(_prod(tmp_path, cors_origins=("https://app.example.com",)))) as c:
        assert c.get("/ready").json()["status"] == "ready"


def test_invalid_environment_and_numbers_are_rejected():
    with pytest.raises(ConfigError):
        load_settings({"ENVIRONMENT": "prod"})
    with pytest.raises(ConfigError):
        load_settings({"RAVEN_MAX_BODY_BYTES": "lots"})
    with pytest.raises(ConfigError):
        load_settings({"RAVEN_MAX_BODY_BYTES": "10"})


# ── Operations ────────────────────────────────────────────────────────────────

def test_ready_reports_unwritable_storage(keyed, tmp_path):
    settings = Settings(data_dir=tmp_path / "missing")
    with TestClient(main.create_app(settings)) as c:
        r = c.get("/ready")
        assert r.status_code == 503 and r.json()["checks"]["data_dir_writable"] is False


def test_status_does_not_disclose_environment(keyed):
    with client_for() as c:
        assert "environment" not in c.get("/status").json()


def test_metrics_count_requests_errors_and_analyses(keyed):
    with client_for() as c:
        c.post("/v1/analyze", json=BODY, headers={"X-API-Key": CUSTOMER})
        c.get("/beta/impact-summary", headers={"X-API-Key": "bad"})
        counters = c.get("/ops/metrics", headers={"X-API-Key": MASTER}).json()["counters"]
        assert counters["analyses"] == 1 and counters["auth_failures"] == 1
        assert counters["responses_2xx"] >= 1 and counters["responses_4xx"] >= 1


def test_unhandled_error_returns_request_id_and_no_internals(keyed, monkeypatch):
    def boom(_):
        raise RuntimeError("-".join(["secret", "internal", "detail"]))
    monkeypatch.setattr(main, "sentinel_evaluate", boom)
    with TestClient(main.create_app(load_settings({})), raise_server_exceptions=False) as c:
        r = c.post("/evaluate", json={"action": "x"}, headers={"X-API-Key": CUSTOMER})
        assert r.status_code == 500
        assert "secret-internal-detail" not in r.text and r.json()["request_id"]
    assert METRICS_5XX() >= 1


def METRICS_5XX() -> int:
    from raven.api.ops import METRICS
    return METRICS.snapshot().get("responses_5xx", 0)


def test_logs_never_contain_keys_or_analysed_content(keyed, caplog, monkeypatch):
    def boom(_):
        raise RuntimeError("-".join(["leaks", "message", "secret"]))
    caplog.set_level(logging.DEBUG)
    secret_text = "confidential-customer-incident-narrative"
    with client_for() as c:
        c.post("/v1/analyze", json={"message": secret_text, "source": "application"},
               headers={"X-API-Key": CUSTOMER})
        c.get("/beta/impact-summary", headers={"X-API-Key": "wrong-key-value-123"})
        monkeypatch.setattr(main, "sentinel_evaluate", boom)
    with TestClient(main.create_app(load_settings({})), raise_server_exceptions=False) as c:
        c.post("/evaluate", json={"message": secret_text}, headers={"X-API-Key": CUSTOMER})
    logged = "\n".join(r.getMessage() for r in caplog.records)
    for forbidden in (CUSTOMER, MASTER, "wrong-key-value-123", secret_text, "leaks-message-secret"):
        assert forbidden not in logged
    assert "rid=" in logged  # access log is present


def test_forged_path_cannot_inject_log_lines(keyed, caplog):
    caplog.set_level(logging.INFO)
    with client_for() as c:
        c.get("/nope%0aFAKE%20LOG%20LINE")
    assert not any("\nFAKE" in r.getMessage() for r in caplog.records)
