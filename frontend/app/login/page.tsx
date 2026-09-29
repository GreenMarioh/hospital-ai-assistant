"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Alert, Button, Card, Field } from "@/components/ui";
import { HOME, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const user = await login(email, password);
      router.replace(HOME[user.role]);
    } catch (err) {
      setError(errorMessage({ detail: (err as Error).message }));
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-md p-6">
      <h1 className="mb-4 text-2xl font-bold">Sign in</h1>
      <Card>
        <form onSubmit={submit} className="space-y-4">
          {error && <Alert kind="error">{error}</Alert>}
          <Field
            label="Email"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Field
            label="Password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </Card>
      <p className="mt-4 text-sm">
        New patient?{" "}
        <Link className="text-blue-800 underline" href="/register">
          Create an account
        </Link>
        {" · "}
        <Link className="text-blue-800 underline" href="/forgot-password">
          Forgot password?
        </Link>
      </p>
      <p className="mt-6 text-xs text-slate-600">
        If you are having a medical emergency, call your local emergency number. This portal is not for
        emergencies.
      </p>
    </main>
  );
}
