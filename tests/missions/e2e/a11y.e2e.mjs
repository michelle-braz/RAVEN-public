// Accessibility and responsive check for Cyber Missions: WCAG 2.x A/AA rules (axe-core), no horizontal
// scroll, no console errors — desktop and mobile, light and dark.
// Usage: BASE_URL=http://127.0.0.1:8765/missions/ node tests/missions/e2e/a11y.e2e.mjs
// Needs `playwright` and `@axe-core/playwright` (PLAYWRIGHT_MODULE / AXE_MODULE override the import paths).
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || "playwright");
const axeMod = await import(process.env.AXE_MODULE || "@axe-core/playwright");
const AxeBuilder = axeMod.default?.default || axeMod.default || axeMod.AxeBuilder;
import assert from "node:assert/strict";
import { mkdirSync, readFileSync } from "node:fs";

const BASE = process.env.BASE_URL || "http://127.0.0.1:8765/missions/";
const SHOTS = process.env.SHOTS_DIR || "";
const data = JSON.parse(readFileSync(new URL("../../../src/raven/missions/web/missions.json", import.meta.url)));
const MISSION = `#/missao/${data.missions[0].id}`;
const ROUTES = ["#/", MISSION, "#/historico", "#/revisar", "#/arquivo", "#/backup"];
const VIEWPORTS = { mobile: { width: 390, height: 844 }, desktop: { width: 1280, height: 800 } };
if (SHOTS) mkdirSync(SHOTS, { recursive: true });

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
const failures = [];
let checks = 0;
for (const [vpName, viewport] of Object.entries(VIEWPORTS)) {
  for (const scheme of ["light", "dark"]) {
    const ctx = await browser.newContext({ viewport, colorScheme: scheme });
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    for (const route of ROUTES) {
      await page.goto(BASE + route);
      await page.locator("#app > *").first().waitFor();
      assert.doesNotMatch(await page.locator("#app").innerText(), /Página não encontrada/, `${vpName}/${scheme}/${route} did not render`);
      const label = `${vpName}/${scheme}/${route}`;
      const { violations } = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
      for (const v of violations) failures.push(`${label}: ${v.id} — ${v.help} (${v.nodes.length} nodes)`);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      if (overflow > 1) failures.push(`${label}: horizontal overflow of ${overflow}px`);
      checks += 1;
      if (SHOTS && (route === "#/" || route === MISSION)) {
        await page.screenshot({ path: `${SHOTS}/missions-${vpName}-${scheme}-${route === "#/" ? "home" : "mission"}.png` });
      }
    }
    if (errors.length) failures.push(`${vpName}/${scheme}: console errors: ${errors.join(" | ")}`);
    await ctx.close();
  }
}
await browser.close();
assert.equal(failures.length, 0, "\n" + failures.join("\n"));
console.log(`A11Y OK — ${checks} page/theme/viewport combinations, no axe violations, no overflow, no console errors.`);
