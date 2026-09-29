import { expect, test } from "@playwright/test";
import { ADMIN, localDateInTz, login, logout } from "./helpers";

const stamp = Date.now();
const patient = {
  first: "E2E",
  last: `Patient${stamp}`,
  email: `e2e.${stamp}@example.com`,
  password: "E2e!Password-12345",
};

test.describe.serial("register → triage → book → doctor briefing → visit note → admin", () => {
  let bookedStart = "";

  test("patient registers and lands in the portal", async ({ page }) => {
    await page.goto("/register");
    await page.getByLabel("First name").fill(patient.first);
    await page.getByLabel("Last name").fill(patient.last);
    await page.getByLabel("Date of birth").fill("1991-05-17");
    await page.getByLabel("Email").fill(patient.email);
    await page.getByLabel("Password").fill(patient.password);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByRole("heading", { name: new RegExp(`Welcome, ${patient.first}`) })).toBeVisible();
  });

  test("triage chat: red flags show the emergency banner without the AI; AI outage degrades gracefully", async ({
    page,
  }) => {
    await login(page, patient.email, patient.password);
    await page.getByRole("link", { name: "Symptom check & FAQ" }).click();

    await page.getByLabel("Describe your symptoms").fill("I have crushing chest pain and my left arm hurts");
    await page.getByRole("button", { name: "Send" }).click();
    const banner = page.getByRole("alert").filter({ hasText: "may be a medical emergency" });
    await expect(banner).toBeVisible();
    await expect(page.getByLabel("Triage result")).toContainText("emergency");
    await expect(page.getByLabel("Triage result")).toContainText("Emergency");
    await expect(page.getByText("AI-generated, requires clinician review").first()).toBeVisible();

    await page.getByRole("button", { name: "Start a new check" }).click();
    await page.getByLabel("Describe your symptoms").fill("I have a mild headache for two days");
    await page.getByRole("button", { name: "Send" }).click();
    await expect(page.getByText("The assistant is unavailable right now").first()).toBeVisible();

    await page.getByLabel(/Ask about visiting hours/).fill("What are the visiting hours for the ICU?");
    await page.getByRole("button", { name: "Ask" }).click();
    await expect(page.getByText(/ICU visits are limited/)).toBeVisible();
  });

  test("patient books an appointment with the cardiologist", async ({ page }) => {
    await login(page, patient.email, patient.password);
    await page.getByRole("link", { name: "Book appointment" }).click();
    await page.getByLabel("Department").selectOption({ label: "Cardiology" });
    await page.getByLabel("Doctor").selectOption({ label: "Dr. Asha Rao (Cardiology)" });
    const first = page.getByRole("button", { name: /^Book / }).first();
    await expect(first).toBeVisible();
    const [resp] = await Promise.all([
      page.waitForResponse((r) => r.url().endsWith("/api/appointments") && r.request().method() === "POST"),
      first.click(),
    ]);
    expect(resp.status()).toBe(201);
    bookedStart = (await resp.json()).starts_at;
    await expect(page.getByText(/Booked for/)).toBeVisible();
    await expect(page).toHaveURL(/\/patient\/appointments/);
    await expect(page.getByText("Dr. Asha Rao").first()).toBeVisible();
  });

  test("doctor sees the appointment and AI briefing, then adds a visit note", async ({ page }) => {
    await login(page, "doctor1@hospital.example.com");
    await expect(page.getByRole("heading", { name: "My schedule" })).toBeVisible();
    await page.getByLabel("Go to date").fill(localDateInTz(bookedStart));
    await page.getByRole("button", { name: "Week" }).click();
    const chip = page.getByRole("button", { name: new RegExp(`${patient.first} ${patient.last}`) });
    await expect(chip).toBeVisible();
    await chip.click();
    await page.getByRole("link", { name: /Open chart/ }).click();

    await expect(page.getByRole("heading", { name: `${patient.first} ${patient.last}` })).toBeVisible();
    await page.getByRole("button", { name: "Generate briefing" }).click();
    await expect(page.getByText("AI service unavailable: showing a structured overview")).toBeVisible();
    await expect(page.getByText("AI-generated, requires clinician review").first()).toBeVisible();

    await page.getByLabel("Chief complaint").fill("Palpitations on exertion");
    await page.getByLabel("Notes").fill("Patient reports palpitations for one week.");
    await page.getByLabel("Diagnosis (clinician-entered)").fill("Under investigation");
    await page.getByLabel("Heart rate").fill("88");
    await page.getByRole("button", { name: "Save visit note" }).click();
    await expect(page.getByText("Visit note saved.")).toBeVisible();
    await expect(page.getByText("Palpitations on exertion").first()).toBeVisible();
    await expect(page.getByText("Patient reports palpitations for one week.")).toBeVisible();
  });

  test("patient sees the visit note in their records", async ({ page }) => {
    await login(page, patient.email, patient.password);
    await page.getByRole("link", { name: "My records" }).click();
    await expect(page.getByText(/Palpitations on exertion/).first()).toBeVisible();
    await expect(page.getByText("AI summary")).toHaveCount(0);
  });

  test("route guards: a patient cannot open the admin area", async ({ page }) => {
    await login(page, patient.email, patient.password);
    await page.goto("/admin");
    await expect(page).toHaveURL(/\/patient/);
  });

  test("admin sees the dashboard and audit logs for the flow", async ({ page }) => {
    await login(page, ADMIN.email, ADMIN.password);
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByText("No-show rate")).toBeVisible();
    await expect(page.getByText("AI assistant usage")).toBeVisible();
    await page.getByRole("link", { name: "Audit logs" }).click();
    await expect(page.getByRole("heading", { name: "Audit logs" })).toBeVisible();
    await page.getByLabel("Resource").fill("patients/visits");
    await page.getByRole("button", { name: "Apply filters" }).click();
    await expect(page.getByRole("table")).toContainText("patients/visits");
    await logout(page);
  });
});
