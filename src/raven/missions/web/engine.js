// Cyber Missions — motor de avaliação e progressão.
// Funções puras, sem DOM: testadas com `node --test tests/missions`.
//
// A avaliação segue a lógica RAVEN: separar evidência de hipótese,
// apontar o que faltou observar, sugerir o próximo passo e registrar
// recorrência de erros entre missões.

export const STORAGE_KEY = "cyber-missions:v1";
export const MAX_HINTS = 3;
export const STUCK_ATTEMPTS = 2;
export const REVEAL_AFTER_ATTEMPTS = 3;
export const MIN_ANSWER_WORDS = 4;
export const MIN_EXPLANATION_WORDS = 15;

export function normalize(text) {
  return String(text ?? "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function wordCount(text) {
  const t = normalize(text);
  return t ? t.split(" ").filter((w) => /[a-z0-9]/.test(w)).length : 0;
}

function matchesAny(text, patterns) {
  return (patterns || []).some((p) => new RegExp(p, "i").test(text));
}

// ── Fato × hipótese ───────────────────────────────────────────────────────────

const CERTAINTY = [
  "\\b(e|eh|foi|esta|estao|sao|era|temos) (sendo )?(um |uma |o |a )?(claramente |com certeza |certamente )?(ataque|atacante|invasor|invasao|hacker|criminoso|malicios\\w*|malware|virus|ransomware|golpe|golpista|phishing|minerador|backdoor|trojan|webshell|botnet|comprometid\\w*|hackead\\w*|invadid\\w*|roubad\\w*|vazad\\w*|exfiltra\\w*|culpad\\w*|infectad\\w*)",
  "\\b(com certeza|certamente|sem duvida|definitivamente|obviamente|com toda certeza|100%|ja sabemos que|esta provado|prova que|confirma que)\\b",
  "\\b(o|a) (usuari\\w*|funcionari\\w*|colaborador\\w*) (roubou|vazou|atacou|invadiu|mentiu)",
];

const HEDGE =
  "\\b(provavel\\w*|possivel\\w*|talvez|pode|podem|poderia|parece\\w*|hipotese|suspeit\\w*|indica\\w*|sugere\\w*|sugerem|aparent\\w*|nao (da|e possivel) (para )?(afirmar|saber|confirmar)|ainda nao|precis\\w* (verificar|confirmar|investigar|checar)|se for|caso seja|acho|acredito|desconfio|nao sei|sera que|evidencia)\\b";

// Devolve o trecho tratado como fato, ou null.
export function detectCertainty(text) {
  const sentences = normalize(text).split(/[.!?;\n]+/);
  for (const s of sentences) {
    if (new RegExp(HEDGE).test(s)) continue;
    for (const p of CERTAINTY) {
      const m = s.match(new RegExp(p));
      if (m) return m[0].trim();
    }
  }
  return null;
}

export function factVsHypothesisMessage(mission, claim) {
  return (
    `Até agora sabemos apenas que ${mission.factsKnown}. Isso é evidência. ` +
    `Afirmar "${claim}" ainda é uma hipótese. Reescreva usando ` +
    `"provavelmente", "a evidência indica" ou "minha hipótese é" — e diga ` +
    `que evidência confirmaria isso.`
  );
}

// ── Avaliação da hipótese ─────────────────────────────────────────────────────

export function evaluateAnswer(mission, answer, context = {}) {
  const text = normalize(answer);
  const words = wordCount(answer);
  if (words < MIN_ANSWER_WORDS) {
    return {
      tooShort: true,
      passed: false,
      message:
        "Escreva sua hipótese em pelo menos uma frase completa. " +
        "Comece por: o que aconteceu? O que sabemos de fato?",
    };
  }

  const found = [];
  const missed = [];
  let got = 0;
  let total = 0;
  for (const c of mission.rubric) {
    const w = c.weight ?? 1;
    total += w;
    if (matchesAny(text, c.patterns)) {
      found.push(c);
      got += w;
    } else {
      missed.push(c);
    }
  }
  const missedRequired = missed.filter((c) => c.required);
  const score = total ? got / total : 0;
  const passed = missedRequired.length === 0;

  const misconceptions = (mission.misconceptions || [])
    .filter((m) => matchesAny(text, m.patterns))
    .map((m) => m.feedback);

  const claim = detectCertainty(answer);
  const factCheck = claim ? factVsHypothesisMessage(mission, claim) : null;

  // Recorrência: conceitos que já faltaram em missões anteriores.
  const history = context.missedTags || {};
  const recurrence = [];
  const tagsNow = missed.filter((c) => c.required).map((c) => c.tag).filter(Boolean);
  if (factCheck) tagsNow.push("fato-vs-hipotese");
  for (const tag of tagsNow) {
    const prev = (history[tag] || []).filter((id) => id !== mission.id);
    if (prev.length) recurrence.push({ tag, missions: prev });
  }

  let verdict;
  if (passed && score >= 0.75 && !factCheck) verdict = "solid";
  else if (passed) verdict = "good";
  else if (found.length) verdict = "partial";
  else verdict = "off";

  return {
    tooShort: false,
    passed,
    verdict,
    score: Math.round(score * 100) / 100,
    found: found.map((c) => ({ id: c.id, text: c.praise })),
    missed: missed.map((c) => ({ id: c.id, required: !!c.required, text: c.missFeedback, tag: c.tag })),
    misconceptions,
    factCheck,
    recurrence,
    missedTags: tagsNow,
  };
}

export const VERDICT_LABEL = {
  solid: "Investigação sólida",
  good: "Hipótese sustentada — com pontos a refinar",
  partial: "No caminho — ainda falta uma peça central",
  off: "Ainda não chegou lá — volte às evidências",
};

// ── Explicação com as próprias palavras ──────────────────────────────────────

export function checkExplanation(mission, text) {
  const words = wordCount(text);
  if (words < MIN_EXPLANATION_WORDS) {
    return {
      ok: false,
      message: `Explique em pelo menos ${MIN_EXPLANATION_WORDS} palavras (agora: ${words}). Imagine alguém que nunca estudou cibersegurança.`,
    };
  }
  const t = normalize(text);
  const touches = mission.rubric.some((c) => c.required && matchesAny(t, c.patterns));
  return {
    ok: true,
    message: touches
      ? "Boa explicação — ela conecta a evidência com o conceito."
      : "Registrado. Dica: numa próxima vez, cite a evidência concreta que levou à conclusão.",
  };
}

// ── XP ───────────────────────────────────────────────────────────────────────

export function computeXp(mission, run) {
  const base = mission.boss ? 200 : 100;
  let xp = base - 15 * (run.hintsUsed || 0);
  if (run.passed && run.attempts === 1) xp += 25;
  if (!run.passed) xp = Math.round(xp * 0.5);
  return Math.max(30, xp);
}

// ── Estado e progressão ──────────────────────────────────────────────────────

export function emptyState() {
  return { version: 1, xp: 0, completed: {}, missedTags: {}, drafts: {}, marked: {}, archive: {} };
}

export function currentIndex(missions, state) {
  const i = missions.findIndex((m) => !state.completed[m.id]);
  return i === -1 ? missions.length : i;
}

export function isUnlocked(missions, state, missionId) {
  const idx = missions.findIndex((m) => m.id === missionId);
  if (idx === -1) return false;
  return idx <= currentIndex(missions, state);
}

export function recordMissedTags(state, missionId, tags) {
  for (const tag of tags) {
    const list = state.missedTags[tag] || (state.missedTags[tag] = []);
    if (!list.includes(missionId)) list.push(missionId);
  }
}

export function shouldArchive(mission, run) {
  return !!mission.boss || !!mission.portfolio || (run.passed && run.hintsUsed <= 1 && run.attempts <= 2);
}

// Conclui a missão. Rejeita missões bloqueadas ou sem explicação válida.
export function completeMission(missions, state, mission, run) {
  if (!isUnlocked(missions, state, mission.id)) throw new Error("missão bloqueada");
  if (!checkExplanation(mission, run.explanation).ok) throw new Error("explicação obrigatória");
  if (!run.passed && run.attempts < REVEAL_AFTER_ATTEMPTS) throw new Error("hipótese ainda não analisada");
  if (state.completed[mission.id]) return { xp: 0, already: true };

  const xp = computeXp(mission, run);
  state.xp += xp;
  state.completed[mission.id] = {
    at: new Date().toISOString(),
    xp,
    attempts: run.attempts,
    hintsUsed: run.hintsUsed,
    passed: run.passed,
    firstTry: run.passed && run.attempts === 1,
    hypothesis: run.hypothesis,
    notes: run.notes || "",
    explanation: run.explanation,
    missedFirst: run.missedFirst || [],
  };
  if (shouldArchive(mission, run)) state.archive[mission.id] = true;
  delete state.drafts[mission.id];
  return { xp, already: false };
}

// ── Revisão ──────────────────────────────────────────────────────────────────

export function reviewItems(missions, state) {
  const byId = Object.fromEntries(missions.map((m) => [m.id, m]));
  const done = missions.filter((m) => state.completed[m.id]);
  const errors = done.filter((m) => !state.completed[m.id].firstTry);
  const manyHints = done.filter((m) => state.completed[m.id].hintsUsed >= 2);
  const marked = done.filter((m) => state.marked[m.id]);
  const recurring = Object.entries(state.missedTags)
    .filter(([, ids]) => ids.length >= 2)
    .map(([tag, ids]) => ({ tag, missions: ids.map((id) => byId[id]).filter(Boolean) }));
  return { errors, manyHints, marked, recurring };
}

export function caseMarkdown(mission, record) {
  const ev = mission.evidence.map((e) => `- ${e.label}: ${e.value}`).join("\n");
  return [
    `# Caso ${mission.ticket} — ${mission.title}`,
    "",
    `**Situação**\n\n${mission.situation}`,
    "",
    `**Evidências**\n\n${ev}`,
    "",
    `**Minha hipótese**\n\n${record.hypothesis}`,
    "",
    `**Minha investigação**\n\n${record.notes || "(sem notas)"}\n\nTentativas: ${record.attempts} · Pistas usadas: ${record.hintsUsed}`,
    "",
    `**Conclusão**\n\n${mission.conclusion}\n\nPróximo passo: ${mission.nextStep}`,
    "",
    `**O que aprendi**\n\n${record.explanation}`,
    "",
    "_Caso simulado — dados sintéticos._",
  ].join("\n");
}

export function parseState(raw) {
  try {
    const s = JSON.parse(raw);
    if (!s || s.version !== 1 || typeof s.completed !== "object") return emptyState();
    return { ...emptyState(), ...s };
  } catch {
    return emptyState();
  }
}
