"use client";

import Link from "next/link";
import { useState } from "react";
import { AuthFrame } from "@/components/AuthFrame";
import { Alert, Button, Field } from "@/components/ui";
import { api, unwrap } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <AuthFrame>
      <h1 className="page-title">Reset your password</h1>
      <p className="mb-8 mt-2 text-[15px] text-slate-600">We will email you a link to choose a new one.</p>
      <div>
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
      </div>
      <p className="mt-6 flex justify-between border-t border-line pt-6 text-sm">
        <Link className="link" href="/login">
          Back to sign in
        </Link>
        <Link className="link" href="/reset-password">
          I have a reset token
        </Link>
      </p>
    </AuthFrame>
  );
}
