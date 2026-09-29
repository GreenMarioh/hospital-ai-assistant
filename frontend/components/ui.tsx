"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { errorMessage } from "@/lib/api";

export function cx(...c: (string | false | null | undefined)[]) {
  return c.filter(Boolean).join(" ");
}

export function Button({
  variant = "primary",
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" }) {
  const styles = {
    primary: "bg-blue-700 text-white hover:bg-blue-800 disabled:bg-blue-300",
    secondary: "bg-white text-slate-800 border border-slate-400 hover:bg-slate-100 disabled:text-slate-400",
    danger: "bg-red-700 text-white hover:bg-red-800 disabled:bg-red-300",
  }[variant];
  return (
    <button
      {...props}
      className={cx(
        "rounded px-3 py-2 text-sm font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed",
        styles,
        className,
      )}
    />
  );
}

export function Field({
  label,
  error,
  hint,
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: string }) {
  const id = useId();
  return (
    <div className={className}>
      <label htmlFor={id} className="block text-sm font-medium text-slate-800">
        {label}
      </label>
      <input
        id={id}
        {...props}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-err` : hint ? `${id}-hint` : undefined}
        className="mt-1 w-full rounded border border-slate-500 bg-white px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
      />
      {hint && !error && (
        <p id={`${id}-hint`} className="mt-1 text-xs text-slate-600">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-err`} className="mt-1 text-xs text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}

export function Select({
  label,
  children,
  className,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement> & { label: string }) {
  const id = useId();
  return (
    <div className={className}>
      <label htmlFor={id} className="block text-sm font-medium text-slate-800">
        {label}
      </label>
      <select
        id={id}
        {...props}
        className="mt-1 w-full rounded border border-slate-500 bg-white px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
      >
        {children}
      </select>
    </div>
  );
}

export function Card({
  title,
  actions,
  children,
  className,
}: {
  title?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cx("rounded-lg border border-slate-300 bg-white p-4 shadow-sm", className)}>
      {(title || actions) && (
        <div className="mb-3 flex items-center justify-between gap-2">
          {title && <h2 className="text-base font-semibold text-slate-900">{title}</h2>}
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function Alert({
  kind = "info",
  children,
}: {
  kind?: "info" | "error" | "success" | "warning" | "emergency";
  children: React.ReactNode;
}) {
  const styles = {
    info: "border-blue-300 bg-blue-50 text-blue-900",
    error: "border-red-300 bg-red-50 text-red-900",
    success: "border-green-300 bg-green-50 text-green-900",
    warning: "border-amber-400 bg-amber-50 text-amber-900",
    emergency: "border-red-700 bg-red-700 text-white font-semibold",
  }[kind];
  return (
    <div
      role={kind === "error" || kind === "emergency" ? "alert" : "status"}
      className={cx("rounded border px-3 py-2 text-sm", styles)}
    >
      {children}
    </div>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center gap-2 py-6 text-sm text-slate-700">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-400 border-t-transparent" />
      {label}…
    </div>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <p className="py-6 text-center text-sm text-slate-600">{children}</p>;
}

export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  return (
    <div className="space-y-2 py-4">
      <Alert kind="error">{errorMessage(error instanceof Error ? { detail: error.message } : error)}</Alert>
      {retry && (
        <Button variant="secondary" onClick={retry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function Badge({ children, tone = "slate" }: { children: React.ReactNode; tone?: string }) {
  const tones: Record<string, string> = {
    slate: "bg-slate-200 text-slate-900",
    green: "bg-green-100 text-green-900",
    red: "bg-red-100 text-red-900",
    amber: "bg-amber-100 text-amber-900",
    blue: "bg-blue-100 text-blue-900",
  };
  return (
    <span className={cx("rounded px-2 py-0.5 text-xs font-medium", tones[tone] ?? tones.slate)}>
      {children}
    </span>
  );
}

export const statusTone = (s: string) =>
  ({ booked: "blue", completed: "green", cancelled: "slate", no_show: "red" })[s] ?? "slate";

export const AI_DISCLAIMER =
  "AI-generated decision support, not a diagnosis or medical advice. Requires clinician review. In an emergency call your local emergency number.";

export function AiDisclaimer() {
  return (
    <p className="rounded bg-slate-100 px-3 py-2 text-xs text-slate-700">
      <strong>AI-generated, requires clinician review.</strong> {AI_DISCLAIMER}
    </p>
  );
}

/** Load data with explicit loading / error states and a reload function. */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [state, setState] = useState<{ data?: T; error?: unknown; loading: boolean }>({ loading: true });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(fn, deps);
  const reload = useCallback(() => {
    setState((s) => ({ ...s, loading: true, error: undefined }));
    run().then(
      (data) => setState({ data, loading: false }),
      (error) => setState({ error, loading: false }),
    );
  }, [run]);
  useEffect(() => {
    let live = true;
    run().then(
      (data) => live && setState({ data, loading: false }),
      (error) => live && setState({ error, loading: false }),
    );
    return () => {
      live = false;
    };
  }, [run]);
  return { ...state, reload };
}
