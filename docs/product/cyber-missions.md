# Cyber Missions

> Classification: Product

Cyber Missions is a daily, ticket-based cybersecurity practice built on RAVEN's
investigation structure. Each day opens one mission; the learner investigates,
forms a hypothesis, gets teaching feedback, explains in their own words, and
unlocks the next mission.

## Daily flow

```text
open → today's mission → ticket → situation → evidence → main question
     → hypothesis (+ up to 3 hints) → feedback → "o que lembrar"
     → explain in own words (required) → mission complete (XP) → next mission
```

## How it connects to RAVEN

| RAVEN concept        | In Cyber Missions                                               |
|----------------------|-----------------------------------------------------------------|
| evidence             | the ticket's evidence block; "Evidência importante" in feedback |
| hypothesis           | "Minha hipótese"; fact-vs-hypothesis correction                  |
| impact               | boss and triage missions ask for impact explicitly               |
| next steps           | "Próximo passo do investigador" after each mission               |
| recurrence           | concepts missed in more than one mission are flagged in feedback and in REVISAR |

## Content

`src/raven/missions/web/missions.json` holds 33 missions following the
schedule 29/09 → 31/10 (Redes, Windows e Linux, Segurança e Triagem,
Logs e SIEM, Wireshark, Portfólio e Entrevista), with a boss mission at the
end of four modules and the 17/10 milestone. All data is synthetic.

Each mission has a rubric: concepts with regex patterns (over lower-cased,
accent-free text), marked `required` when the hypothesis must contain them.
Feedback lists what was noticed, what was missed, the key evidence, and —
once the central concepts are present or after three attempts — what it means.

## Running

- Through the RAVEN API: `python -m uvicorn raven.api.main:app` and open
  `http://127.0.0.1:8000/missions/` (public, no API key).
- As a static site: serve `src/raven/missions/web/` with any static host
  (`vercel.json` in the repository root does this on Vercel, with a strict CSP).

## Data and privacy

Progress (completed missions, XP, the learner's own written answers) is stored **only in the browser**
(`localStorage`). There is no account, no server-side storage, no cookie, no analytics and no external
request; the page loads nothing from third parties (CSP `default-src 'self'`). The "Backup do progresso" page
copies or restores that data by hand. Clearing site data erases it.

## Language

The interface and the mission content are Brazilian Portuguese by design (the audience is Portuguese-speaking
learners). Documentation, code and API are English.

## Tests

```bash
python -m pytest tests -q                   # includes the JS engine suite when node is installed
node --test tests/missions/*.test.mjs       # engine only
# Browser checks against a running server (need `playwright`; the accessibility check also needs `@axe-core/playwright`):
BASE_URL=http://127.0.0.1:8000/missions/ MISSIONS_TO_PLAY=33 node tests/missions/e2e/flow.e2e.mjs   # all 33 missions, mobile
BASE_URL=http://127.0.0.1:8000/missions/ node tests/missions/e2e/a11y.e2e.mjs                       # WCAG A/AA, 2 viewports x 2 themes
```

Results: [validation report](../validation/readiness-report.md).
