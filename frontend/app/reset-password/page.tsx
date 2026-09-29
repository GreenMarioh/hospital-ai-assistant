"use client";

import Link from "next/link";
import { useState } from "react";
import { Alert, Button, Card, Field } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";

export default function ResetPasswordPage() {
  const [token, setToken] = useState("");
  const [pw, setPw] = useState("");
  const [state, setState] = useState<"idle" | "done" | string>("idle");
  return (
    <main className="mx-auto max-w-md p-6">
      <h1 className="mb-4 text-2xl font-bold">Choose a new password</h1>
      <Card>
        {state === "done" ? (
          <Alert kind="success">
            Password updated.{" "}
            <Link className="underline" href="/login">
              Sign in
            </Link>
          </Alert>
        ) : (
          <form
            className="space-y-4"
            onSubmit={async (e) => {
              e.preventDefault();
              const res = await api.POST("/api/auth/reset-password", { body: { token, new_password: pw } });
              setState(res.response.ok ? "done" : errorMessage(res.error));
            }}
          >
            {state !== "idle" && <Alert kind="error">{state}</Alert>}
            <Field label="Reset token" required value={token} onChange={(e) => setToken(e.target.value)} />
            <Field
              label="New password"
              type="password"
              required
              minLength={12}
              autoComplete="new-password"
              hint="At least 12 characters"
              value={pw}
              onChange={(e) => setPw(e.target.value)}
            />
            <Button type="submit" className="w-full">
              Update password
            </Button>
          </form>
        )}
      </Card>
    </main>
  );
}
