"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Alert, Button, Card, Field } from "@/components/ui";
import { HOME } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [f, setF] = useState({
    first_name: "",
    last_name: "",
    email: "",
    password: "",
    date_of_birth: "",
    phone: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setF({ ...f, [k]: e.target.value });
  const weak = f.password.length > 0 && f.password.length < 12;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const user = await register({ ...f, phone: f.phone || undefined });
      router.replace(HOME[user.role]);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-md p-6">
      <h1 className="mb-4 text-2xl font-bold">Create patient account</h1>
      <Card>
        <form onSubmit={submit} className="space-y-4">
          {error && <Alert kind="error">{error}</Alert>}
          <div className="grid grid-cols-2 gap-3">
            <Field
              label="First name"
              required
              value={f.first_name}
              onChange={set("first_name")}
              autoComplete="given-name"
            />
            <Field
              label="Last name"
              required
              value={f.last_name}
              onChange={set("last_name")}
              autoComplete="family-name"
            />
          </div>
          <Field
            label="Date of birth"
            type="date"
            required
            value={f.date_of_birth}
            onChange={set("date_of_birth")}
            autoComplete="bday"
          />
          <Field
            label="Phone (optional)"
            type="tel"
            value={f.phone}
            onChange={set("phone")}
            autoComplete="tel"
          />
          <Field
            label="Email"
            type="email"
            required
            value={f.email}
            onChange={set("email")}
            autoComplete="email"
          />
          <Field
            label="Password"
            type="password"
            required
            value={f.password}
            onChange={set("password")}
            autoComplete="new-password"
            hint="At least 12 characters"
            error={weak ? "Password must be at least 12 characters" : undefined}
          />
          <Button type="submit" disabled={busy || weak} className="w-full">
            {busy ? "Creating…" : "Create account"}
          </Button>
        </form>
      </Card>
      <p className="mt-4 text-sm">
        Already registered?{" "}
        <Link className="text-blue-800 underline" href="/login">
          Sign in
        </Link>
      </p>
    </main>
  );
}
