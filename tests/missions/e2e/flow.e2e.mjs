// Validação ponta a ponta do fluxo diário no navegador real.
// Uso: BASE_URL=http://127.0.0.1:8765/missions/ node tests/missions/e2e/flow.e2e.mjs
// (requer `playwright`; para uma instalação global use PLAYWRIGHT_MODULE=$(npm root -g)/playwright/index.mjs)
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || "playwright");
import assert from "node:assert/strict";
import { readFileSync, mkdirSync } from "node:fs";

const BASE = process.env.BASE_URL || "http://127.0.0.1:8765/missions/";
const SHOTS = process.env.SHOTS_DIR || "";
const N = Number(process.env.MISSIONS_TO_PLAY || 3);
const samples = JSON.parse(readFileSync(new URL("../samples.json", import.meta.url)));
const data = JSON.parse(readFileSync(new URL("../../../src/raven/missions/web/missions.json", import.meta.url)));
const EXPLANATION =
  "Quando dois computadores conversam, cada um tem um endereço e cada serviço tem uma porta. Olhando esses dados dá para entender quem falou com quem e o que foi usado.";

if (SHOTS) mkdirSync(SHOTS, { recursive: true });
const shot = async (page, name) => SHOTS && page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));

await page.goto(BASE);
await page.getByText("CYBER MISSIONS", { exact: true }).first().waitFor();
assert.match(await page.locator(".today").innerText(), /Missão #001/);
assert.match(await page.locator(".today").innerText(), new RegExp(`0 / ${data.missions.length}`));
await shot(page, "01-home");

let totalXp = 0;
for (let i = 0; i < N; i++) {
  const m = data.missions[i];
  const s = samples[m.id];
  await page.locator("#continuar, #proxima").first().click();
  await page.locator(".ticket").waitFor();
  const ticket = await page.locator(".ticket").innerText();
  assert.match(ticket, new RegExp(`TICKET ${m.ticket}`));
  assert.match(ticket, /Em investigação/);
  for (const h of ["Situação", "Evidências", "Pergunta principal"]) await page.getByRole("heading", { name: h }).waitFor();
  if (i === 0) await shot(page, "02-mission-open");

  // Tentativa fraca → feedback que ensina, sem entregar a explicação.
  await page.fill("#hipotese", s.weak[0]);
  await page.click("#analisar");
  const fb = page.locator("#feedback");
  await fb.waitFor();
  const fbText = await fb.innerText();
  for (const sec of ["O que você percebeu corretamente", "O que faltou observar", "Evidência importante", "O que isso significa"]) {
    assert.ok(fbText.includes(sec), `${m.id}: feedback sem "${sec}"`);
  }
  assert.ok(!fbText.includes(m.meaning), "explicação completa não pode aparecer antes de acertar");
  assert.match(await page.locator("#status").innerText(), /Hipótese em análise/);
  assert.equal(await page.locator("#explicacao").count(), 0, "explicar só depois de sustentar a hipótese");

  // Hipótese tratada como fato (missão 1) → correção fato × hipótese.
  if (i === 0) {
    await page.fill("#hipotese", "Esse IP é um atacante invadindo a empresa pelo notebook do financeiro.");
    await page.click("#analisar");
    await page.locator(".factcheck").waitFor();
    assert.match(await page.locator(".factcheck").innerText(), /Até agora sabemos apenas que/);
    assert.equal(await page.locator("#stuck").isVisible(), true, "anti-travamento após 2 tentativas");
    await shot(page, "03-fact-vs-hypothesis");
  }

  // Pistas: uma por vez, no máximo 3.
  await page.click("#pedir-pista");
  await page.locator("#hints li").first().waitFor();
  assert.match(await page.locator("#hints").innerText(), /Pista 1/);
  if (i === 0) {
    await page.click("#pedir-pista");
    await page.click("#pedir-pista");
    assert.equal(await page.locator("#hints li").count(), 3);
    assert.equal(await page.locator("#pedir-pista").isDisabled(), true);
    await shot(page, "04-hints");
  }

  // Resposta boa → hipótese sustentada → O que lembrar + explicar.
  await page.fill("#hipotese", s.good[0]);
  await page.click("#analisar");
  await page.locator("#explicacao").waitFor();
  assert.ok((await page.locator("#feedback").innerText()).includes(m.meaning));
  assert.match(await page.locator(".remember").innerText(), new RegExp(m.remember.slice(0, 20).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  if (i === 0) await shot(page, "05-feedback-ok");

  // Explicação é obrigatória.
  await page.fill("#explicacao", "é sobre ip");
  await page.click("#concluir");
  assert.match(await page.locator("#explicacao-msg").innerText(), /pelo menos/);
  await page.fill("#explicacao", EXPLANATION);
  await page.click("#concluir");

  await page.getByText("MISSÃO CONCLUÍDA").waitFor();
  const done = await page.locator(".done").textContent();
  for (const k of ["XP ganho", "Habilidade aprendida", "Pistas usadas", "Conceito principal", "Próxima missão"]) assert.ok(done.includes(k), k);
  const xp = Number((await page.locator("#xp-ganho").innerText()).match(/\d+/)[0]);
  assert.ok(xp > 0);
  totalXp += xp;
  if (i === 0) await shot(page, "06-done");

  const next = data.missions[i + 1];
  if (next) {
    assert.match(done, new RegExp(`${next.ticket}.*desbloqueada`));
    if (i === N - 1) break;
    await page.click("#proxima");
    await page.locator(".ticket").waitFor();
    await page.click("a.back");
  }
}

// Progresso continua salvo depois de fechar e voltar.
await page.goto(BASE);
await page.reload();
const home = await page.locator(".today").innerText();
assert.match(home, new RegExp(`${N} / ${data.missions.length}`));
assert.match(home, new RegExp(String(totalXp)));
await shot(page, "07-home-after");

// Missão bloqueada não abre.
const locked = data.missions[N + 1];
if (locked) {
  await page.goto(BASE + `#/missao/${locked.id}`);
  await page.getByText(/está bloqueado/).waitFor();
}

// Revisar missão antiga mostra minha hipótese e explicação.
await page.goto(BASE + `#/missao/${data.missions[0].id}`);
assert.ok((await page.locator("article").innerText()).includes(EXPLANATION));
await page.goto(BASE + "#/revisar");
await page.getByRole("heading", { name: "REVISAR", exact: true }).waitFor();
assert.match(await page.locator("main").textContent(), /Missões em que usei muitas pistas.*#001/s);
await page.goto(BASE + "#/arquivo");
await page.getByRole("heading", { name: "Arquivo de casos" }).waitFor();
await shot(page, "08-archive");

assert.deepEqual(errors, [], `erros no console: ${errors.join(" | ")}`);
await browser.close();
console.log(`E2E OK — ${N} missões concluídas, ${totalXp} XP, progresso persistido.`);
