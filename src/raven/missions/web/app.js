// Cyber Missions — interface. Toda a lógica de avaliação vive em engine.js.
import {
  STORAGE_KEY, MAX_HINTS, STUCK_ATTEMPTS, REVEAL_AFTER_ATTEMPTS,
  evaluateAnswer, checkExplanation, completeMission,
  currentIndex, isUnlocked, recordMissedTags, reviewItems, caseMarkdown,
  parseState, emptyState, VERDICT_LABEL,
} from "./engine.js";

const STUCK_MS = 4 * 60 * 1000;
const REASONING = [
  "O que aconteceu?",
  "O que sabemos de fato?",
  "O que parece estranho?",
  "Qual é minha hipótese?",
  "Que evidência sustentaria essa hipótese?",
  "O que eu verificaria depois?",
];

let DATA = null;
let state = emptyState();
let practice = {}; // treinos sem XP (só na memória)
let stuckTimer = null;
const app = document.getElementById("app");

// ── Persistência ─────────────────────────────────────────────────────────────

function load() {
  try { state = parseState(localStorage.getItem(STORAGE_KEY)); } catch { state = emptyState(); }
}
function save() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* modo privado */ }
  renderTopXp();
}

// ── Helpers de DOM (sempre textContent, nunca innerHTML com dados) ──────────

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === false || v == null) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "text") el.textContent = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}
const section = (title, ...body) => h("section", { class: "block" }, h("h2", {}, title), ...body);

function mount(...nodes) {
  clearTimeout(stuckTimer);
  app.replaceChildren(...nodes);
  app.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}

const missions = () => DATA.missions;
const moduleOf = (m) => DATA.modules.find((x) => x.id === m.module);
const byId = (id) => missions().find((m) => m.id === id);
const nextOf = (m) => missions()[missions().indexOf(m) + 1];
const fmtDate = (iso) => iso.slice(8, 10) + "/" + iso.slice(5, 7);
const todayIso = () => new Date().toLocaleDateString("sv-SE");

function renderTopXp() {
  const done = Object.keys(state.completed).length;
  document.getElementById("topxp").textContent = DATA ? `${state.xp} XP · ${done}/${missions().length}` : "";
}

// ── Tela inicial ─────────────────────────────────────────────────────────────

function homeView() {
  const idx = currentIndex(missions(), state);
  const total = missions().length;
  const m = missions()[idx];
  const children = [h("h1", { class: "title" }, "CYBER MISSIONS")];

  if (!m) {
    children.push(
      h("div", { class: "today" },
        h("p", { class: "label" }, "Cronograma concluído"),
        h("p", { class: "big" }, `${total} / ${total} missões · ${state.xp} XP`),
        h("p", {}, "Você fechou todos os casos. Use o Arquivo de casos como material de portfólio."),
      ),
      h("a", { class: "btn primary huge", href: "#/arquivo" }, "ABRIR ARQUIVO DE CASOS"),
    );
  } else {
    const draft = state.drafts[m.id];
    const plan = m.date;
    const today = todayIso();
    let pace = `Planejada para ${fmtDate(plan)}`;
    if (today > plan) pace += " — está um pouco atrás do cronograma. Tudo bem: siga daqui.";
    else if (today < plan) pace += " — você está adiantada.";
    children.push(
      h("div", { class: "today" },
        h("p", { class: "label" }, "Hoje"),
        h("p", { class: "big" }, `Missão ${m.ticket}`, m.boss ? h("span", { class: "boss-tag" }, "BOSS") : null),
        h("p", { class: "mtitle" }, m.title),
        h("dl", { class: "stats" },
          h("div", {}, h("dt", {}, "Módulo"), h("dd", {}, moduleOf(m).name)),
          h("div", {}, h("dt", {}, "Progresso"), h("dd", {}, `${idx} / ${total}`)),
          h("div", {}, h("dt", {}, "XP"), h("dd", {}, String(state.xp))),
        ),
        h("div", { class: "bar", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": String(total), "aria-valuenow": String(idx) },
          progressFill(idx / total)),
        h("p", { class: "pace muted" }, pace),
      ),
      milestoneFor(m, today),
      h("a", { class: "btn primary huge", href: `#/missao/${m.id}`, id: "continuar" },
        draft ? "CONTINUAR MISSÃO" : idx === 0 ? "COMEÇAR MISSÃO" : "CONTINUAR MISSÃO"),
    );
  }
  children.push(
    h("p", { class: "center" }, h("a", { href: "#/historico" }, "Revisar missões anteriores")),
    h("nav", { class: "minor" },
      h("a", { href: "#/revisar" }, "Revisar"), " · ",
      h("a", { href: "#/arquivo" }, "Arquivo de casos"), " · ",
      h("a", { href: "#/backup" }, "Backup do progresso"),
    ),
  );
  mount(h("div", { class: "home" }, ...children));
}

function progressFill(ratio) {
  const el = h("span");
  el.style.width = `${Math.round(ratio * 100)}%`; // CSSOM: permitido pela CSP (sem style inline)
  return el;
}

function milestoneFor(m, today) {
  const hit = missions().find((x) => x.milestone && (x === m || x.date === today));
  return hit ? h("div", { class: "milestone" }, hit.milestone) : null;
}

// ── Missão ───────────────────────────────────────────────────────────────────

function getRun(m) {
  if (practice[m.id]) return practice[m.id];
  if (!state.drafts[m.id]) {
    state.drafts[m.id] = {
      hypothesis: "", notes: "", explanation: "", attempts: 0, hintsUsed: 0,
      passed: false, revealed: false, lastResult: null, missedFirst: null, startedAt: Date.now(),
    };
    save();
  }
  return state.drafts[m.id];
}

function persist(m) { if (!practice[m.id]) save(); }

function missionView(id) {
  const m = byId(id);
  if (!m) return notFound();
  if (!isUnlocked(missions(), state, id)) return lockedView(m);
  if (state.completed[id] && !practice[id]) return reviewCaseView(m);

  const run = getRun(m);
  const isPractice = !!practice[id];
  const hints = m.hints.slice(0, MAX_HINTS);
  const status = run.passed || run.revealed ? "Hipótese sustentada" : run.attempts ? "Hipótese em análise" : "Em investigação";

  const hintList = h("ol", { class: "hints", id: "hints" },
    hints.slice(0, run.hintsUsed).map((t, i) => h("li", {}, h("strong", {}, `Pista ${i + 1}: `), t)));
  const hintBtn = h("button", {
    class: "btn", id: "pedir-pista", type: "button", disabled: run.hintsUsed >= hints.length,
    onclick: () => { run.hintsUsed++; persist(m); missionView(id); focusEl("#hints li:last-child"); },
  }, run.hintsUsed >= hints.length ? `Sem mais pistas (${hints.length}/${hints.length})` : `PEDIR PISTA (${run.hintsUsed}/${hints.length})`);

  const hyp = h("textarea", {
    id: "hipotese", rows: "5", placeholder: "Ex.: A evidência indica que… Minha hipótese é… Eu verificaria…",
    oninput: (e) => { run.hypothesis = e.target.value; persist(m); },
  });
  hyp.value = run.hypothesis;

  const notes = h("textarea", {
    id: "notas", rows: m.boss ? "6" : "3", placeholder: REASONING.join("\n"),
    oninput: (e) => { run.notes = e.target.value; persist(m); },
  });
  notes.value = run.notes;

  const analyze = () => {
    const result = evaluateAnswer(m, run.hypothesis, { missedTags: state.missedTags });
    if (!result.tooShort) {
      run.attempts++;
      if (run.missedFirst === null) run.missedFirst = result.missed.filter((x) => x.required).map((x) => x.id);
      if (result.passed) run.passed = true;
      if (!isPractice) recordMissedTags(state, m.id, result.missedTags);
    }
    run.lastResult = result;
    persist(m);
    missionView(id);
    focusEl("#feedback");
  };

  const stuck = !run.passed && run.attempts >= STUCK_ATTEMPTS;
  const nodes = [
    h("a", { class: "back", href: "#/" }, "← Início"),
    isPractice ? h("p", { class: "practice" }, "Modo treino — refazendo sem XP. Seu registro original fica preservado.") : null,
    ticketCard(m, status),
    milestoneFor(m, null),
    section("Situação", h("p", {}, m.situation)),
    section("Evidências", evidenceList(m)),
    h("section", { class: "block question" }, h("h2", {}, "Pergunta principal"), h("p", { class: "q" }, m.question)),
    m.qa?.length ? h("aside", { class: "qa" }, h("strong", {}, "Pergunta de QA: "), m.qa.join(" ")) : null,
    h("details", { class: "block reasoning", open: m.boss || !!run.notes },
      h("summary", {}, "Roteiro do investigador · minhas notas (opcional)"),
      h("ul", { class: "reasoning-list" }, REASONING.map((q) => h("li", {}, q))),
      h("label", { for: "notas", class: "sr" }, "Notas de investigação"), notes),
    h("section", { class: "block" }, h("h2", {}, "Pistas"),
      hintList,
      run.hintsUsed === 0 ? h("p", { class: "muted" }, "Tente primeiro. Se precisar, peça uma pista — cada uma revela um pouco mais.") : null,
      hintBtn),
    h("section", { class: "block" },
      h("h2", {}, h("label", { for: "hipotese" }, "Minha hipótese")),
      hyp,
      h("div", { class: "row" },
        h("button", { class: "btn primary", id: "analisar", type: "button", onclick: analyze }, "ANALISAR RESPOSTA"),
        h("span", { class: "muted" }, run.attempts ? `Tentativas: ${run.attempts}` : "")),
    ),
    h("div", { class: "stuck", id: "stuck", hidden: !stuck, role: "status" },
      "Travou? Não fique parada. Peça uma pista, registre a dúvida nas notas e continue."),
    run.lastResult ? feedbackPanel(m, run) : null,
    run.passed || run.revealed ? explainPanel(m, run, isPractice) : null,
  ];
  mount(h("article", { class: "mission" }, ...nodes));

  if (!run.passed && !stuck) {
    const elapsed = Date.now() - (run.startedAt || Date.now());
    stuckTimer = setTimeout(() => {
      const el = document.getElementById("stuck");
      if (el) el.hidden = false;
    }, Math.max(0, STUCK_MS - elapsed));
  }
}

function focusEl(sel) {
  const el = document.querySelector(sel);
  if (el) { el.setAttribute("tabindex", "-1"); el.focus({ preventScroll: true }); el.scrollIntoView({ behavior: "smooth", block: "start" }); }
}

function ticketCard(m, status) {
  return h("header", { class: "ticket" },
    h("p", { class: "tnum" }, `TICKET ${m.ticket}`, m.boss ? h("span", { class: "boss-tag" }, "BOSS MISSION") : null),
    h("h1", {}, m.title),
    h("dl", { class: "tmeta" },
      h("div", {}, h("dt", {}, "Área"), h("dd", {}, moduleOf(m).name)),
      h("div", {}, h("dt", {}, "Dificuldade"), h("dd", {}, m.difficulty)),
      h("div", {}, h("dt", {}, "Status"), h("dd", { id: "status" }, status)),
      h("div", {}, h("dt", {}, "Data"), h("dd", {}, fmtDate(m.date))),
    ),
  );
}

function evidenceList(m) {
  return h("dl", { class: "evidence" },
    m.evidence.map((e) => h("div", {}, h("dt", {}, e.label), h("dd", {}, h("pre", {}, e.value)))));
}

function feedbackPanel(m, run) {
  const r = run.lastResult;
  if (r.tooShort) return h("section", { class: "feedback warn", id: "feedback" }, h("p", {}, r.message));

  const showMeaning = run.passed || run.revealed;
  const got = r.found.length
    ? h("ul", {}, r.found.map((f) => h("li", {}, f.text)))
    : h("p", {}, "Ainda não apareceu na sua resposta nenhum dos pontos centrais. Tudo bem — volte às evidências e use uma pista.");
  const missing = r.missed.filter((x) => x.required || showMeaning || r.found.length);
  const miss = missing.length
    ? h("ul", {}, missing.map((x) => h("li", { class: x.required ? "req" : "" }, x.text, x.required ? h("em", {}, " (central)") : null)))
    : h("p", {}, "Nada importante ficou de fora. Excelente leitura das evidências.");

  const nodes = [
    h("p", { class: `verdict v-${r.verdict}` }, VERDICT_LABEL[r.verdict]),
    r.factCheck ? h("div", { class: "factcheck" }, h("strong", {}, "Fato × hipótese. "), r.factCheck) : null,
    r.misconceptions.length ? h("div", { class: "misc" }, h("strong", {}, "Atenção a um conceito: "), r.misconceptions.join(" ")) : null,
    h("h3", {}, "O que você percebeu corretamente"), got,
    h("h3", {}, "O que faltou observar"), miss,
    h("h3", {}, "Evidência importante"), h("p", { class: "mono" }, m.keyEvidence),
    h("h3", {}, "O que isso significa"),
    showMeaning
      ? h("p", {}, m.meaning)
      : h("p", { class: "muted" }, "A explicação completa aparece quando sua hipótese cobrir os pontos centrais. Ajuste e analise de novo."),
    r.recurrence.length
      ? h("p", { class: "recurrence" }, h("strong", {}, "Recorrência: "),
          r.recurrence.map((x) => `isso também faltou em ${x.missions.map((id) => byId(id)?.ticket || id).join(", ")}`).join("; "),
          ". Vale revisar.")
      : null,
    showMeaning ? h("p", {}, h("strong", {}, "Próximo passo do investigador: "), m.nextStep) : null,
  ];
  if (!run.passed && !run.revealed && run.attempts >= REVEAL_AFTER_ATTEMPTS) {
    nodes.push(h("button", {
      class: "btn", id: "revelar", type: "button",
      onclick: () => { run.revealed = true; persist(m); missionView(m.id); focusEl("#explicar-bloco"); },
    }, "Ver a explicação completa e seguir"));
  }
  return h("section", { class: "feedback", id: "feedback", "aria-live": "polite" }, h("h2", {}, "Feedback"), ...nodes);
}

function explainPanel(m, run, isPractice) {
  const ta = h("textarea", {
    id: "explicacao", rows: "5",
    placeholder: "Com minhas palavras: …",
    oninput: (e) => { run.explanation = e.target.value; persist(m); },
  });
  ta.value = run.explanation;
  const msg = h("p", { class: "muted", id: "explicacao-msg", "aria-live": "polite" });
  const finish = () => {
    const check = checkExplanation(m, run.explanation);
    msg.textContent = check.message;
    if (!check.ok) { msg.className = "warn-text"; ta.focus(); return; }
    run.hypothesis = run.hypothesis.trim();
    if (isPractice) {
      delete practice[m.id];
      location.hash = `#/missao/${m.id}`;
      return;
    }
    const res = completeMission(missions(), state, m, run);
    state.lastRun = { id: m.id, xp: res.xp, hintsUsed: run.hintsUsed, explanationMsg: check.message };
    save();
    location.hash = `#/concluida/${m.id}`;
  };
  return h("section", { class: "block explain", id: "explicar-bloco" },
    h("div", { class: "remember" }, h("h2", {}, "O que lembrar"), h("p", {}, m.remember)),
    h("h2", {}, h("label", { for: "explicacao" }, "Explique com suas palavras")),
    h("p", {}, "Agora explique o que você aprendeu como se estivesse explicando para alguém que nunca estudou cibersegurança."),
    ta, msg,
    h("button", { class: "btn primary", id: "concluir", type: "button", onclick: finish },
      isPractice ? "CONCLUIR TREINO" : "CONCLUIR MISSÃO"),
  );
}

// ── Conclusão ────────────────────────────────────────────────────────────────

function doneView(id) {
  const m = byId(id);
  const rec = m && state.completed[id];
  if (!rec) return homeView();
  const next = nextOf(m);
  const mark = h("input", {
    type: "checkbox", id: "marcar", checked: !!state.marked[id],
    onchange: (e) => { if (e.target.checked) state.marked[id] = true; else delete state.marked[id]; save(); },
  });
  mount(h("article", { class: "done" },
    h("p", { class: "tnum" }, `TICKET ${m.ticket} · Status: Resolvido`),
    h("h1", { class: "done-title" }, "MISSÃO CONCLUÍDA"),
    h("dl", { class: "summary" },
      h("div", {}, h("dt", {}, "XP ganho"), h("dd", { id: "xp-ganho" }, `+${rec.xp} XP`)),
      h("div", {}, h("dt", {}, "Habilidade aprendida"), h("dd", {}, m.skill)),
      h("div", {}, h("dt", {}, "Pistas usadas"), h("dd", {}, `${rec.hintsUsed} de ${m.hints.length}`)),
      h("div", {}, h("dt", {}, "Conceito principal"), h("dd", {}, m.remember)),
      h("div", {}, h("dt", {}, "Próxima missão"), h("dd", {}, next ? `${next.ticket} — ${next.title} (desbloqueada)` : "Cronograma completo!")),
    ),
    state.lastRun?.id === id ? h("p", { class: "muted" }, state.lastRun.explanationMsg) : null,
    state.archive[id] ? h("p", { class: "ok-text" }, "Esta investigação foi guardada no Arquivo de casos.") : null,
    h("p", {}, h("label", {}, mark, " Marcar para revisar")),
    next
      ? h("a", { class: "btn primary huge", id: "proxima", href: `#/missao/${next.id}` }, "ABRIR PRÓXIMA MISSÃO")
      : h("a", { class: "btn primary huge", href: "#/arquivo" }, "ABRIR ARQUIVO DE CASOS"),
    h("p", { class: "center" }, h("a", { href: "#/" }, "Voltar ao início")),
  ));
}

// ── Revisão de missão concluída ──────────────────────────────────────────────

function reviewCaseView(m) {
  const rec = state.completed[m.id];
  const toggle = (key, label) => h("label", { class: "toggle" },
    h("input", {
      type: "checkbox", checked: !!state[key][m.id],
      onchange: (e) => { if (e.target.checked) state[key][m.id] = true; else delete state[key][m.id]; save(); },
    }), " ", label);
  mount(h("article", { class: "mission review" },
    h("a", { class: "back", href: "#/historico" }, "← Missões anteriores"),
    ticketCard(m, "Resolvido"),
    section("Situação", h("p", {}, m.situation)),
    section("Evidências", evidenceList(m)),
    section("Pergunta principal", h("p", {}, m.question)),
    section("Minha hipótese", h("p", { class: "mine" }, rec.hypothesis || "—")),
    rec.notes ? section("Minhas notas de investigação", h("p", { class: "mine" }, rec.notes)) : null,
    section("Conclusão do caso", h("p", {}, m.conclusion), h("p", {}, h("strong", {}, "Próximo passo: "), m.nextStep)),
    section("O que isso significa", h("p", {}, m.meaning)),
    h("div", { class: "remember" }, h("h2", {}, "O que lembrar"), h("p", {}, m.remember)),
    section("O que eu aprendi (minhas palavras)", h("p", { class: "mine" }, rec.explanation)),
    h("p", { class: "muted" }, `Tentativas: ${rec.attempts} · Pistas: ${rec.hintsUsed} · XP: ${rec.xp}`),
    h("div", { class: "row" }, toggle("marked", "Marcar para revisar"), toggle("archive", "Guardar no Arquivo de casos")),
    h("button", {
      class: "btn", type: "button", id: "treinar",
      onclick: () => {
        practice[m.id] = { hypothesis: "", notes: "", explanation: "", attempts: 0, hintsUsed: 0, passed: false, revealed: false, lastResult: null, missedFirst: null, startedAt: Date.now() };
        missionView(m.id);
      },
    }, "Treinar de novo (sem XP)"),
  ));
}

function lockedView(m) {
  const cur = missions()[currentIndex(missions(), state)];
  mount(h("article", { class: "locked" },
    h("h1", {}, `Ticket ${m.ticket} está bloqueado`),
    h("p", {}, "Uma missão por vez. Conclua a missão atual para desbloquear a próxima — assim nenhum conteúdo fica para trás."),
    cur ? h("a", { class: "btn primary", href: `#/missao/${cur.id}` }, `Ir para a missão ${cur.ticket}`) : null,
  ));
}

function notFound() {
  mount(h("div", {}, h("p", {}, "Página não encontrada."), h("a", { href: "#/" }, "Voltar ao início")));
}

// ── Histórico, Revisar, Arquivo, Backup ──────────────────────────────────────

function missionLink(m, extra) {
  return h("li", {}, h("a", { href: `#/missao/${m.id}` }, `${m.ticket} — ${m.title}`), extra ? h("span", { class: "muted" }, ` · ${extra}`) : null);
}

function historyView() {
  const blocks = DATA.modules.map((mod) => {
    const ms = missions().filter((m) => m.module === mod.id);
    const items = ms.map((m) => {
      const rec = state.completed[m.id];
      if (rec) return missionLink(m, `${rec.xp} XP · ${rec.hintsUsed} pista(s)`);
      if (isUnlocked(missions(), state, m.id)) return missionLink(m, "em andamento");
      return h("li", { class: "locked-item" }, `${m.ticket} — 🔒 bloqueada (${fmtDate(m.date)})`);
    });
    return h("section", { class: "block" },
      h("h2", {}, `${mod.name} · ${mod.dates}`), h("p", { class: "muted" }, `Meta: ${mod.goal}`), h("ul", { class: "plain" }, items));
  });
  mount(h("div", {}, h("a", { class: "back", href: "#/" }, "← Início"), h("h1", {}, "Missões anteriores"), ...blocks));
}

function reviseView() {
  const r = reviewItems(missions(), state);
  const TAGS = Object.fromEntries(missions().flatMap((m) => m.rubric.map((c) => [c.tag, c.missFeedback])));
  const list = (arr, fmt) => arr.length ? h("ul", { class: "plain" }, arr.map(fmt)) : h("p", { class: "muted" }, "Nada aqui por enquanto.");
  mount(h("div", {},
    h("a", { class: "back", href: "#/" }, "← Início"),
    h("h1", {}, "REVISAR"),
    section("Conceitos em que errei",
      list(r.errors, (m) => missionLink(m, m.remember))),
    section("Missões em que usei muitas pistas",
      list(r.manyHints, (m) => missionLink(m, `${state.completed[m.id].hintsUsed} pistas`))),
    section("Marcadas para revisar",
      list(r.marked, (m) => missionLink(m))),
    r.recurring.length ? section("Pontos cegos recorrentes",
      h("ul", { class: "plain" }, r.recurring.map((x) => h("li", {},
        h("strong", {}, x.tag === "fato-vs-hipotese" ? "Tratar hipótese como fato" : TAGS[x.tag] || x.tag),
        h("span", { class: "muted" }, ` · ${x.missions.map((m) => m.ticket).join(", ")}`))))) : null,
  ));
}

function archiveView() {
  const cases = missions().filter((m) => state.archive[m.id] && state.completed[m.id]);
  const items = cases.map((m) => {
    const md = caseMarkdown(m, state.completed[m.id]);
    const rec = state.completed[m.id];
    return h("details", { class: "block case" },
      h("summary", {}, `${m.ticket} — ${m.title}`, m.boss ? " · BOSS" : ""),
      h("h3", {}, "Situação"), h("p", {}, m.situation),
      h("h3", {}, "Evidências"), evidenceList(m),
      h("h3", {}, "Minha hipótese"), h("p", { class: "mine" }, rec.hypothesis),
      h("h3", {}, "Minha investigação"), h("p", { class: "mine" }, rec.notes || "(sem notas)"),
      h("p", { class: "muted" }, `Tentativas: ${rec.attempts} · Pistas: ${rec.hintsUsed}`),
      h("h3", {}, "Conclusão"), h("p", {}, m.conclusion),
      h("h3", {}, "O que aprendi"), h("p", { class: "mine" }, rec.explanation),
      h("button", {
        class: "btn", type: "button",
        onclick: (e) => copy(md, e.target),
      }, "Copiar como Markdown (portfólio)"),
    );
  });
  mount(h("div", {},
    h("a", { class: "back", href: "#/" }, "← Início"),
    h("h1", {}, "Arquivo de casos"),
    h("p", { class: "muted" }, "Suas melhores investigações são guardadas aqui automaticamente (poucas pistas, boss missions e casos de portfólio). Você também pode guardar qualquer missão pela tela de revisão."),
    items.length ? items : h("p", {}, "Nenhum caso arquivado ainda. Conclua uma missão com até 1 pista para ver seu primeiro caso aqui."),
  ));
}

async function copy(text, btn) {
  try { await navigator.clipboard.writeText(text); btn.textContent = "Copiado!"; }
  catch { btn.textContent = "Não foi possível copiar"; }
}

function backupView() {
  const out = h("textarea", { rows: "6", readonly: true, id: "backup-out" });
  out.value = JSON.stringify(state);
  const inp = h("textarea", { rows: "4", id: "backup-in", placeholder: "Cole aqui um backup para restaurar" });
  const msg = h("p", { class: "muted", "aria-live": "polite" });
  mount(h("div", {},
    h("a", { class: "back", href: "#/" }, "← Início"),
    h("h1", {}, "Backup do progresso"),
    h("p", {}, "Seu progresso fica salvo neste navegador. Para usar em outro aparelho, copie o backup e cole lá."),
    out,
    h("button", { class: "btn", type: "button", onclick: (e) => copy(out.value, e.target) }, "Copiar backup"),
    h("h2", {}, "Restaurar"), inp,
    h("button", {
      class: "btn", type: "button",
      onclick: () => {
        const s = parseState(inp.value);
        if (!inp.value.trim() || (!Object.keys(s.completed).length && !s.xp)) { msg.textContent = "Backup inválido ou vazio."; return; }
        state = s; save(); msg.textContent = "Progresso restaurado.";
      },
    }, "Restaurar backup"),
    msg,
  ));
}

// ── Roteamento ───────────────────────────────────────────────────────────────

function route() {
  const [, view, id] = (location.hash || "#/").split("/");
  renderTopXp();
  if (view === "missao" && id) return missionView(id);
  if (view === "concluida" && id) return doneView(id);
  if (view === "historico") return historyView();
  if (view === "revisar") return reviseView();
  if (view === "arquivo") return archiveView();
  if (view === "backup") return backupView();
  return homeView();
}

async function start() {
  load();
  try {
    const res = await fetch("missions.json", { cache: "no-cache" });
    DATA = await res.json();
  } catch {
    app.replaceChildren(h("p", {}, "Não foi possível carregar as missões. Recarregue a página."));
    return;
  }
  window.addEventListener("hashchange", route);
  route();
}

start();
