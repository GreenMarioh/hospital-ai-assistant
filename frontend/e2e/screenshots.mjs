// Regenerates docs/screenshots/*.png against a running stack: node e2e/screenshots.mjs
import { chromium } from "@playwright/test";

const BASE = process.env.E2E_BASE_URL ?? "http://localhost:3000";
const OUT = new URL("../../docs/screenshots/", import.meta.url).pathname;
const browser = await chromium.launch();

async function session(email, password) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/login`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"));
  return page;
}

let page = await session("patient1@example.com", "DemoPass!12345");
await page.getByRole("link", { name: "Symptom check & FAQ" }).click();
await page.getByLabel("Describe your symptoms").fill("I have crushing chest pain and my left arm hurts");
await page.getByRole("button", { name: "Send" }).click();
await page.getByRole("alert").filter({ hasText: "may be a medical emergency" }).waitFor();
await page.screenshot({ path: `${OUT}patient-triage.png` });

page = await session("doctor1@hospital.example.com", "DemoPass!12345");
await page.getByRole("link", { name: "My patients" }).click();
const withHistory = page.getByRole("link", { name: /Open chart for E2E/ });
await ((await withHistory.count()) > 0 ? withHistory.first() : page.getByRole("link", { name: /Open chart/ }).first()).click();
await page.getByRole("button", { name: /Generate briefing|Regenerate/ }).click();
await page.getByRole("button", { name: "Regenerate briefing" }).waitFor();
await page.getByText(/Flagged items|AI service unavailable/).first().waitFor();
await page.screenshot({ path: `${OUT}doctor-briefing.png`, fullPage: false });

page = await session("admin@hospital.example.com", "ChangeMe!12345");
await page.getByText("No-show rate").waitFor();
await page.waitForTimeout(800);
await page.screenshot({ path: `${OUT}admin-dashboard.png` });
await browser.close();
console.log("screenshots written to", OUT);
