# STATUS — RAVEN

> Documento de retomada. Lendo este arquivo você consegue voltar exatamente ao ponto em que paramos, sem reconstruir contexto.
> Última atualização: 2026-08-21 · Branch: `claude/slack-session-1nmor4`

## Contexto honesto desta sessão

Ao abrir a sessão, a árvore de trabalho já estava **limpa** (`git status` = "nothing to commit, working tree clean") e a branch `claude/slack-session-1nmor4` era **idêntica à `main`**: um único commit `458afbe Initial public release of RAVEN`. **Não havia trabalho não commitado a recuperar** — nada funcional foi perdido, mas também não havia alterações pendentes desta sessão além deste `STATUS.md`.

O que esta sessão fez: **verificou** o estado real do projeto (build/import/testes) e registrou o resultado aqui.

## O que está implementado

Projeto **RAVEN**: API REST de análise de incidentes / memória operacional em **Python 3.11+ / FastAPI** (layout `src/`, empacotamento setuptools, testes com pytest). ~3.474 linhas em `src/raven/`.

Estrutura principal:
- `src/raven/api/` — `main.py` (app FastAPI), `auth.py` (autenticação via header `X-API-Key`), `beta_keys.py`, `landing.html`
  - `api/v1/` — `router.py`, `enrichment.py`
  - `api/beta/` — `router.py`, `store.py`, `models.py`
- `src/raven/sentinel/` — motor do pipeline
  - `core/` — `engine.py`, `rules.py`, `models.py` (motor de regras legado)
  - `pipeline/` — `app.py`, `contracts.py`
    - `signal_layer/normalizer.py` — normalização/scrubbing (timestamps, UUIDs, IPs, hashes → tokens tipados `<ts>`, `<uuid>` etc.)
    - `intelligence_layer/engine.py` — scoring determinístico multifator (~604 linhas)
    - `action_layer/notifier.py` — despacho de ações
    - `data_layer/schemas.py`
  - `observability/buffer.py`

Endpoints expostos:
- `GET /` — landing HTML
- `GET /health` — healthcheck
- `GET /status` — status do serviço
- `POST /evaluate` — motor de regras legado (inteiros)
- `POST /v1/analyze` — pipeline principal de análise
- `POST /beta/validate-resolution` e demais rotas `/beta/*` — memória de resolução/feedback + resumo de impacto

## O que está funcionando de verdade (verificado nesta sessão)

- **Instalação editável**: `python -m pip install -e ".[dev]"` → sucesso (exit 0). `python -m pip check` → "No broken requirements found."
- **Import**: `python -c "import raven; import raven.api.main"` → OK.
- **Testes**: `python -m pytest tests -q` → **69 passed, 0 failed** (1 warning não-fatal), em ~1,35s.
- Lógica real (não mock) confirmada por leitura de código e testes:
  - Normalização e deduplicação de sinais (`signal_layer/normalizer.py`).
  - Scoring determinístico multifator, incluindo scoring léxico em PT com folding de diacríticos (`intelligence_layer/engine.py`, coberto por `tests/test_pt_lexical_scoring.py`).
  - Despacho de ações real: `WebhookChannel` faz `httpx` POST com `raise_for_status`; `LogChannel`; `ActionDispatcher` usa `asyncio.gather` com isolamento de falhas (`action_layer/notifier.py`).
  - Autenticação por chave (`free`/`pro`/`beta`) e gate de beta (`api/auth.py`, `api/beta_keys.py`).
  - Memória de resolução/decisão persistida em **JSONL local** (`RAVEN_DATA_DIR`), com gating de aprovação e resumos de impacto (`tests/test_validate_resolution.py`, `tests/test_beta_impact.py`).

Suíte de testes (pytest, 8 arquivos): `test_smoke.py`, `test_public_api.py`, `test_v1_analyze_validation.py`, `test_pt_lexical_scoring.py`, `test_auth_free_keys.py`, `test_beta_impact.py`, `test_validate_resolution.py`, `test_synthetic_examples.py`.

## O que ainda está "simulado" / deliberadamente limitado

Não há stubs, mocks ou "not implemented" no código — mas há limitações de escopo **intencionais** (documentadas em `README.md` "Limitations" e `docs/architecture.md`) que ainda NÃO são grau de produção:

- **Scoring/enriquecimento são heurísticas determinísticas**, não modelos de ML/aprendizado.
- **Janela de recorrência e rate limits são in-memory / por processo** — perdidos ao reiniciar e não compartilhados entre workers.
- **Memória validada usa arquivos JSONL locais**, não banco de dados.
- Sem durabilidade / HA / escala horizontal.
- Sem conector de observabilidade específico de fornecedor incluído.
- Todos os exemplos em `examples/` são **sintéticos**.

## Erros ou bloqueios encontrados

- **Nenhum bloqueio.** Build, import e testes passam.
- **Não há ferramenta de typecheck/lint configurada.** O extra `[dev]` fixa apenas `pytest`; `mypy`, `ruff` e `pyright` não estão instalados. "Typecheck" não pôde ser executado porque não existe no projeto (não foi instalada nenhuma ferramenta nova nesta sessão).
- **Não há passo de build** separado (setuptools/src-layout; a instalação editável é a verificação equivalente).
- Aviso não-fatal nos testes: `StarletteDeprecationWarning` de `fastapi/testclient.py` ("Using httpx with starlette.testclient is deprecated"). Não afeta resultados.
- `.env` **não é carregado automaticamente** — as variáveis precisam ser exportadas no ambiente (ver README).

## Próximo passo exato para continuar amanhã

Como não havia trabalho pendente, a retomada é uma **decisão de direção**, não conserto. Passos naturais, em ordem de menor esforço:

1. `git checkout claude/slack-session-1nmor4 && git pull origin claude/slack-session-1nmor4` para trazer este `STATUS.md`.
2. Escolher UMA das frentes abaixo antes de codar:
   - (a) **Qualidade de base**: adicionar `ruff` + `mypy` ao extra `[dev]` no `pyproject.toml`, configurar e rodar — hoje não há gate estático.
   - (b) **Persistência real**: substituir a memória in-memory (recorrência/rate limit) e o JSONL local por um backend durável (SQLite como primeiro passo), preservando os contratos em `sentinel/pipeline/contracts.py`.
   - (c) **CI**: não existe `.github/workflows`; adicionar workflow que rode `pytest` (e o lint/typecheck de (a)) a cada push.
3. Qualquer que seja a escolha, o critério de pronto é: `python -m pytest tests -q` continua **verde** e o número de testes só cresce.

## Comandos exatos para abrir e testar localmente

```bash
# 1. Entrar no repo e na branch
cd RAVEN-public
git checkout claude/slack-session-1nmor4

# 2. (Recomendado) criar e ativar venv
python -m venv .venv && source .venv/bin/activate   # Linux/macOS

# 3. Instalar em modo editável com deps de dev
python -m pip install -e ".[dev]"

# 4. Sanidade de build/import
python -m pip check
python -c "import raven; import raven.api.main; print('import OK')"

# 5. Rodar os testes (esperado: 69 passed)
python -m pytest tests -q

# 6. Subir o servidor localmente
#    (defina ao menos RAVEN_API_KEY; .env NÃO é carregado automaticamente)
export RAVEN_API_KEY="dev-key"
python -m uvicorn raven.api.main:app --host 127.0.0.1 --port 8000
#    -> abrir http://127.0.0.1:8000/ (landing) e http://127.0.0.1:8000/health

# 7. Exemplo de chamada autenticada ao pipeline principal
curl -s http://127.0.0.1:8000/health
# análise: ver payloads de exemplo em examples/synthetic-investigation.http
```

## Base técnica reutilizável (nota para Foxhuman)

Sem alterar ainda o propósito do produto RAVEN, a arquitetura atual é candidata a base técnica reutilizável. Peças com maior potencial de reaproveitamento:

- **Pipeline em camadas** (`signal_layer` → `intelligence_layer` → `action_layer`) com contratos explícitos em `sentinel/pipeline/contracts.py` — separação limpa entre ingestão, decisão e ação.
- **Camada de normalização/scrubbing** (`normalizer.py`) — remoção de PII/identificadores voláteis por regex, útil para qualquer ingestão de logs.
- **Despacho de ações desacoplado** (`action_layer/notifier.py`) — canais plugáveis (webhook/log) com isolamento de falhas via `asyncio.gather`.
- **Camada de autenticação por chave e tiers** (`api/auth.py`, `beta_keys.py`) — reutilizável para gating de features/beta.
- **Memória de resolução/feedback** (`api/beta/`) — padrão de "loop de aprendizado" com persistência simples.

Nenhuma dessas peças foi modificada nesta sessão; a nota é apenas um mapa para reaproveitamento futuro.
