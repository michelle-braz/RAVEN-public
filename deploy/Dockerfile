# syntax=docker/dockerfile:1
# RAVEN — single small image. Build context: the repository root.
FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.lock .
# Behind a TLS-inspecting proxy: docker build --secret id=cacert,src=/path/ca.crt ...
RUN --mount=type=secret,id=cacert,required=false \
    if [ -f /run/secrets/cacert ]; then export PIP_CERT=/run/secrets/cacert; fi; \
    pip install -r requirements.lock
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN --mount=type=secret,id=cacert,required=false \
    if [ -f /run/secrets/cacert ]; then export PIP_CERT=/run/secrets/cacert; fi; \
    pip install --no-deps . \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin raven \
    && mkdir -p /data && chown raven:raven /data && chmod 700 /data
# Third-party licence texts travel with the image.
COPY docs/licensing/THIRD_PARTY_LICENSES.txt /usr/share/doc/raven/THIRD_PARTY_LICENSES.txt
COPY LICENSE /usr/share/doc/raven/LICENSE
USER raven
ENV ENVIRONMENT=production RAVEN_DATA_DIR=/data HOST=0.0.0.0 PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=4s --start-period=15s --retries=4 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/ready', timeout=3)" || exit 1
# One process: recurrence memory and rate limits are per process by design (docs/system/architecture.md).
# The app writes its own access log (no bodies, queries or keys); uvicorn's is disabled and it must not
# rewrite client addresses (RAVEN_TRUSTED_PROXY_HOPS does that explicitly).
CMD ["uvicorn", "raven.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-server-header", "--no-proxy-headers", "--timeout-graceful-shutdown", "20"]
