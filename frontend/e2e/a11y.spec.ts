import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { ADMIN, ensureDoctorHasPatient, login } from "./helpers";

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

async function audit(page: Page, label: string) {
  const results = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  const summary = results.violations.map(
    (v) => `${v.id} (${v.impact}): ${v.nodes.map((n) => n.target.join(" ")).join(" | ")}`,
  );
  expect(summary, `${label} has WCAG 2.1 AA violations`).toEqual([]);
}

test("public pages have no WCAG 2.1 AA violations", async ({ page }) => {
  for (const path of ["/login", "/register", "/forgot-password", "/reset-password"]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await audit(page, path);
  }
});

test("patient portal pages", async ({ page }) => {
  await login(page, "patient1@example.com", "DemoPass!12345");
  for (const [link, heading] of [
    ["Home", /Welcome/],
    ["Symptom check & FAQ", "Symptom check & FAQ"],
    ["Book appointment", "Book an appointment"],
    ["My appointments", "My appointments"],
    ["My records", "My records"],
  ] as const) {
    await page.getByRole("link", { name: link, exact: true }).click();
    await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
    await expect(page.getByRole("status")).toHaveCount(0); // spinners gone
    await audit(page, `patient: ${link}`);
  }
});

test("reception and doctor pages", async ({ page, request }) => {
  await ensureDoctorHasPatient(request);
  await login(page, "staff@hospital.example.com");
  await expect(page.getByRole("heading", { level: 1, name: "Patients", exact: true })).toBeVisible();
  await audit(page, "reception: patients");
  await page.getByRole("link", { name: "Calendar & booking" }).click();
  await page.getByLabel("Doctor").selectOption({ index: 1 });
  await expect(page.getByRole("table").first()).toBeVisible();
  await audit(page, "reception: calendar");
  await page.getByRole("button", { name: "Sign out" }).click();

  await login(page, "doctor1@hospital.example.com");
  await expect(page.getByRole("heading", { level: 1, name: "My schedule" })).toBeVisible();
  await expect(page.getByRole("table")).toBeVisible();
  await audit(page, "doctor: schedule");
  await page.getByRole("link", { name: "My patients" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "My patients" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Open chart/ }).first()).toBeVisible();
  await audit(page, "doctor: patients");
  await page
    .getByRole("link", { name: /Open chart/ })
    .first()
    .click();
  await expect(page.getByRole("button", { name: /briefing/i })).toBeVisible();
  await audit(page, "doctor: chart");
});

test("admin pages", async ({ page }) => {
  await login(page, ADMIN.email, ADMIN.password);
  await expect(page.getByRole("heading", { level: 1, name: "Dashboard" })).toBeVisible();
  await expect(page.getByText("No-show rate")).toBeVisible();
  await audit(page, "admin: dashboard");
  await page.getByRole("link", { name: "Users" }).click();
  await expect(page.getByRole("table")).toBeVisible();
  await audit(page, "admin: users");
  await page.getByRole("link", { name: "Audit logs" }).click();
  await expect(page.getByRole("table")).toBeVisible();
  await audit(page, "admin: audit");
});

test("keyboard: skip link and focus visibility", async ({ page }) => {
  await login(page, "patient1@example.com", "DemoPass!12345");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main/);
});
