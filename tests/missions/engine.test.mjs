// Testes do motor do Cyber Missions: `node --test tests/missions`
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  evaluateAnswer, detectCertainty, checkExplanation, computeXp, completeMission,
  currentIndex, isUnlocked, emptyState, reviewItems, recordMissedTags, parseState, caseMarkdown,
} from "../../src/raven/missions/web/engine.js";

const DATA = JSON.parse(readFileSync(new URL("../../src/raven/missions/web/missions.json", import.meta.url)));
const M = Object.fromEntries(DATA.missions.map((m) => [m.id, m]));
const EXPLANATION = "O endereço IP mostra de onde saiu e para onde foi a conversa, como o endereço de uma casa numa carta enviada.";

// Respostas de referência por missão: uma boa (deve passar) e uma fraca (não deve).
const SAMPLES = JSON.parse(readFileSync(new URL("./samples.json", import.meta.url)));

for (const m of DATA.missions) {
  const s = SAMPLES[m.id];
  test(`${m.id}: amostras de resposta cobertas`, () => {
    assert.ok(s, `faltam amostras para ${m.id}`);
    assert.ok(s.good.length >= 1 && s.weak.length >= 1);
  });
  if (!s) continue;
  for (const answer of s.good) {
    test(`${m.id}: resposta boa passa — "${answer.slice(0, 50)}…"`, () => {
      const r = evaluateAnswer(m, answer);
      assert.equal(r.passed, true, `faltou: ${r.missed.filter((x) => x.required).map((x) => x.id)}`);
    });
  }
  for (const answer of s.weak) {
    test(`${m.id}: resposta fraca não passa — "${answer.slice(0, 50)}…"`, () => {
      const r = evaluateAnswer(m, answer);
      assert.equal(r.passed, false);
      assert.ok(r.missed.some((x) => x.required && x.text));
    });
  }
}

test("resposta curta demais pede frase completa", () => {
  const r = evaluateAnswer(M["redes-01"], "é o google");
  assert.equal(r.tooShort, true);
  assert.equal(r.passed, false);
});

test("hipótese tratada como fato é corrigida", () => {
  const r = evaluateAnswer(M["redes-01"], "Esse IP é um atacante tentando invadir a rede interna.");
  assert.ok(r.factCheck);
  assert.match(r.factCheck, /Até agora sabemos apenas que/);
  assert.match(r.factCheck, /ainda é uma hipótese/);
});

test("hipótese com linguagem de incerteza não é corrigida", () => {
  assert.equal(detectCertainty("Esse IP pode ser um atacante, mas preciso verificar."), null);
  assert.equal(detectCertainty("Provavelmente é um ataque de força bruta."), null);
  assert.ok(detectCertainty("Com certeza o servidor foi hackeado."));
  assert.ok(detectCertainty("O usuário roubou os dados."));
});

test("feedback tem as seções que ensinam", () => {
  const r = evaluateAnswer(M["redes-02"], "A porta 443 indica que o serviço usado é HTTPS, navegação web criptografada.");
  assert.equal(r.passed, true);
  assert.ok(r.found.length >= 2);
  assert.ok(r.found.every((f) => f.text));
});

test("equívoco conhecido gera correção de conceito", () => {
  const r = evaluateAnswer(M["redes-01"], "A origem é um IP público e o destino também está na internet.");
  assert.ok(r.misconceptions.length);
});

test("recorrência aponta missões anteriores com o mesmo erro", () => {
  const r = evaluateAnswer(M["redes-03"], "Com certeza a Ana foi hackeada, a senha foi roubada por um invasor.", {
    missedTags: { "fato-vs-hipotese": ["redes-01"] },
  });
  assert.ok(r.recurrence.some((x) => x.tag === "fato-vs-hipotese" && x.missions.includes("redes-01")));
});

test("explicação com poucas palavras é recusada", () => {
  assert.equal(checkExplanation(M["redes-01"], "ip privado").ok, false);
  assert.equal(checkExplanation(M["redes-01"], EXPLANATION).ok, true);
});

test("XP: pistas reduzem, primeira tentativa bonifica, boss vale mais", () => {
  const m = M["redes-01"];
  assert.equal(computeXp(m, { hintsUsed: 0, attempts: 1, passed: true }), 125);
  assert.equal(computeXp(m, { hintsUsed: 2, attempts: 2, passed: true }), 70);
  assert.equal(computeXp(m, { hintsUsed: 3, attempts: 3, passed: false }), 30);
  const boss = DATA.missions.find((x) => x.boss);
  if (boss) assert.ok(computeXp(boss, { hintsUsed: 0, attempts: 1, passed: true }) > 125);
});

test("progressão: uma por vez, bloqueio e conclusão", () => {
  const ms = DATA.missions;
  const st = emptyState();
  assert.equal(currentIndex(ms, st), 0);
  assert.equal(isUnlocked(ms, st, ms[0].id), true);
  assert.equal(isUnlocked(ms, st, ms[1].id), false);
  assert.throws(() => completeMission(ms, st, ms[1], { attempts: 1, passed: true, hintsUsed: 0, explanation: EXPLANATION }), /bloqueada/);
  assert.throws(() => completeMission(ms, st, ms[0], { attempts: 1, passed: true, hintsUsed: 0, explanation: "curta" }), /explicação/);
  assert.throws(() => completeMission(ms, st, ms[0], { attempts: 1, passed: false, hintsUsed: 0, explanation: EXPLANATION }), /hipótese/);

  const res = completeMission(ms, st, ms[0], { attempts: 1, passed: true, hintsUsed: 1, explanation: EXPLANATION, hypothesis: "h" });
  assert.equal(res.xp, 110);
  assert.equal(st.xp, 110);
  assert.equal(currentIndex(ms, st), 1);
  assert.equal(isUnlocked(ms, st, ms[1].id), true);
  assert.equal(isUnlocked(ms, st, ms[0].id), true, "missões antigas continuam abertas para revisão");
  assert.ok(st.archive[ms[0].id], "boa investigação vai para o arquivo");
  // concluir de novo não dá XP em dobro
  assert.equal(completeMission(ms, st, ms[0], { attempts: 1, passed: true, hintsUsed: 0, explanation: EXPLANATION }).xp, 0);
  assert.equal(st.xp, 110);
});

test("após 3 tentativas sem acertar, pode seguir com XP reduzido", () => {
  const ms = DATA.missions;
  const st = emptyState();
  const res = completeMission(ms, st, ms[0], { attempts: 3, passed: false, hintsUsed: 3, explanation: EXPLANATION, hypothesis: "h" });
  assert.equal(res.xp, 30);
  assert.equal(st.completed[ms[0].id].firstTry, false);
  assert.ok(!st.archive[ms[0].id]);
});

test("revisão lista erros, pistas demais e recorrência", () => {
  const ms = DATA.missions;
  const st = emptyState();
  completeMission(ms, st, ms[0], { attempts: 2, passed: true, hintsUsed: 3, explanation: EXPLANATION, hypothesis: "h" });
  st.marked[ms[0].id] = true;
  recordMissedTags(st, "redes-01", ["fato-vs-hipotese"]);
  recordMissedTags(st, "redes-02", ["fato-vs-hipotese"]);
  const r = reviewItems(ms, st);
  assert.equal(r.errors.length, 1);
  assert.equal(r.manyHints.length, 1);
  assert.equal(r.marked.length, 1);
  assert.equal(r.recurring[0].tag, "fato-vs-hipotese");
});

test("estado persistido sobrevive a JSON e rejeita lixo", () => {
  const st = emptyState();
  st.xp = 42;
  assert.equal(parseState(JSON.stringify(st)).xp, 42);
  assert.equal(parseState("{quebrado").xp, 0);
  assert.equal(parseState(null).xp, 0);
});

test("caso de portfólio em Markdown tem as 6 seções", () => {
  const md = caseMarkdown(M["redes-01"], { hypothesis: "h", notes: "n", attempts: 1, hintsUsed: 0, explanation: "e" });
  for (const s of ["Situação", "Evidências", "Minha hipótese", "Minha investigação", "Conclusão", "O que aprendi"]) {
    assert.match(md, new RegExp(`\\*\\*${s}\\*\\*`));
  }
});
