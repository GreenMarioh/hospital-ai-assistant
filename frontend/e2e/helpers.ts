import { expect, type Page } from "@playwright/test";

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
