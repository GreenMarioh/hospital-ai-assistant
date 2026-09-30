import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const DEMO_PASSWORD = "DemoPass!12345";
export const ADMIN = { email: "admin@hospital.example.com", password: "ChangeMe!12345" };

export async function login(page: Page, email: string, password = DEMO_PASSWORD) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL((url) => !url.pathname.startsWith("/login"));
}

export async function logout(page: Page) {
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
}

export function localDateInTz(iso: string, tz = "Asia/Kolkata") {
  return new Intl.DateTimeFormat("en-CA", { timeZone: tz }).format(new Date(iso));
}

const API = process.env.E2E_API_URL ?? "http://localhost:8000";

/** Make the suite independent of test order: give doctor1 (Cardiology) at least one patient via the API. */
export async function ensureDoctorHasPatient(request: APIRequestContext) {
  const stamp = Date.now();
  const email = `seed.${stamp}@example.com`;
  const password = "Seed!Password-12345";
  const reg = await request.post(`${API}/api/auth/register`, {
    data: { email, password, first_name: "Seed", last_name: `Patient${stamp}`, date_of_birth: "1990-01-01" },
  });
  expect(reg.ok()).toBeTruthy();
  const auth = { Authorization: `Bearer ${(await reg.json()).access_token}` };
  const doctors = await (await request.get(`${API}/api/doctors`, { headers: auth })).json();
  const doctor = doctors.find((d: { name: string }) => d.name === "Dr. Asha Rao");
  const from = new Date().toISOString().slice(0, 10);
  const to = new Date(Date.now() + 13 * 86400000).toISOString().slice(0, 10);
  const slots = await (
    await request.get(`${API}/api/doctors/${doctor.id}/slots?from=${from}&to=${to}`, { headers: auth })
  ).json();
  const book = await request.post(`${API}/api/appointments`, {
    headers: auth,
    data: { doctor_id: doctor.id, starts_at: slots[slots.length - 1].starts_at, reason: "e2e seed" },
  });
  expect(book.ok()).toBeTruthy();
}
