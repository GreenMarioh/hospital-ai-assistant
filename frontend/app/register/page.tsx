"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthFrame } from "@/components/AuthFrame";
import { Alert, Button, Field } from "@/components/ui";
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
    <AuthFrame>
      <h1 className="page-title">Create patient account</h1>
      <p className="mb-8 mt-2 text-[15px] text-slate-600">
        For patients. Staff accounts are set up by the hospital administrator.
      </p>
      <div>
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
      </div>
      <p className="mt-6 border-t border-line pt-6 text-sm text-slate-700">
        Already registered?{" "}
        <Link className="link" href="/login">
          Sign in
        </Link>
      </p>
    </AuthFrame>
  );
}
