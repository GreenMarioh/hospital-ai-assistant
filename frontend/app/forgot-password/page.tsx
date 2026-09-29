"use client";

import Link from "next/link";
import { useState } from "react";
import { Alert, Button, Card, Field } from "@/components/ui";
import { api, unwrap } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <main className="mx-auto max-w-md p-6">
      <h1 className="mb-4 text-2xl font-bold">Reset your password</h1>
      <Card>
        {done ? (
          <Alert kind="success">If an account exists for that email, a reset link has been sent.</Alert>
        ) : (
          <form
            className="space-y-4"
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                unwrap(await api.POST("/api/auth/forgot-password", { body: { email } }));
                setDone(true);
              } catch (err) {
                setError((err as Error).message);
              }
            }}
          >
            {error && <Alert kind="error">{error}</Alert>}
            <Field
              label="Email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <Button type="submit" className="w-full">
              Send reset link
            </Button>
          </form>
        )}
      </Card>
      <p className="mt-4 text-sm">
        <Link className="text-blue-800 underline" href="/reset-password">
          I have a reset token
        </Link>
        {" · "}
        <Link className="text-blue-800 underline" href="/login">
          Back to sign in
        </Link>
      </p>
    </main>
  );
}
