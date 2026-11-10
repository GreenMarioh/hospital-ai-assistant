"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { errorMessage } from "@/lib/api";

export function cx(...c: (string | false | null | undefined)[]) {
  return c.filter(Boolean).join(" ");
}

export function Button({
  variant = "primary",
  size = "md",
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "dangerQuiet";
  size?: "md" | "sm";
}) {
  const styles = {
    primary:
      "bg-navy-800 text-white hover:bg-navy-900 active:bg-navy-950 disabled:bg-navy-200 disabled:text-navy-600",
    secondary:
      "bg-white text-navy-800 border border-navy-200 hover:border-navy-400 hover:bg-navy-50 disabled:border-line disabled:text-slate-500 disabled:hover:bg-white",
    danger: "bg-red-700 text-white hover:bg-red-800 disabled:bg-red-200 disabled:text-red-800",
    /* Starts a destructive flow that asks for confirmation; the confirm step uses "danger". */
    dangerQuiet:
      "bg-white text-red-700 border border-red-200 hover:border-red-400 hover:bg-red-50 disabled:text-red-300",
  }[variant];
  return (
    <button
      {...props}
      className={cx(
        "inline-flex items-center justify-center gap-1.5 rounded-[5px] font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-navy-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed",
        size === "sm" ? "px-2.5 py-1.5 text-[13px]" : "px-3.5 py-2 text-sm",
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
      <label htmlFor={id} className="block text-[13px] font-medium text-navy-900">
        {label}
      </label>
      <input
        id={id}
        {...props}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-err` : hint ? `${id}-hint` : undefined}
        className="mt-1.5 w-full rounded-[5px] border border-slate-400 bg-white px-3 py-2 text-sm text-navy-950 placeholder:text-slate-500 hover:border-navy-400 focus:border-navy-700 focus:outline-none focus:ring-2 focus:ring-navy-100 aria-[invalid]:border-red-700"
      />
      {hint && !error && (
        <p id={`${id}-hint`} className="mt-1.5 text-xs text-slate-600">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-err`} className="mt-1.5 text-xs font-medium text-red-700">
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
      <label htmlFor={id} className="block text-[13px] font-medium text-navy-900">
        {label}
      </label>
      <select
        id={id}
        {...props}
        className="mt-1.5 w-full rounded-[5px] border border-slate-400 bg-white px-3 py-2 text-sm text-navy-950 hover:border-navy-400 focus:border-navy-700 focus:outline-none focus:ring-2 focus:ring-navy-100"
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
    <section className={cx("rounded-lg border border-line bg-white p-5 md:p-6", className)}>
      {(title || actions) && (
        <div className="mb-4 flex items-center justify-between gap-2">
          {title && <h2 className="text-[17px] font-semibold tracking-[-0.005em] text-navy-900">{title}</h2>}
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
    info: "border-navy-600 bg-navy-50 text-navy-900",
    error: "border-red-700 bg-red-50 text-red-900",
    success: "border-emerald-700 bg-emerald-50 text-emerald-900",
    warning: "border-marigold-600 bg-marigold-100 text-[#5C3D06]",
    emergency: "border-red-950 bg-red-700 text-white font-semibold text-[15px] py-3",
  }[kind];
  return (
    <div
      role={kind === "error" || kind === "emergency" ? "alert" : "status"}
      className={cx("rounded-[5px] border-l-4 px-4 py-2.5 text-sm leading-relaxed", styles)}
    >
      {children}
    </div>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center gap-2.5 py-6 text-sm text-slate-600">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-navy-200 border-t-navy-700" />
      {label}…
    </div>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return (
    <p className="rounded-md border border-dashed border-navy-200 px-4 py-8 text-center text-sm text-slate-600">
      {children}
    </p>
  );
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
    slate: "bg-slate-100 text-slate-700 ring-slate-300",
    green: "bg-emerald-50 text-emerald-800 ring-emerald-200",
    red: "bg-red-50 text-red-800 ring-red-200",
    amber: "bg-marigold-100 text-[#5C3D06] ring-marigold-300",
    blue: "bg-navy-50 text-navy-800 ring-navy-200",
  };
  return (
    <span
      className={cx(
        "inline-block whitespace-nowrap rounded-full px-2 py-px text-xs font-medium ring-1 ring-inset",
        tones[tone] ?? tones.slate,
      )}
    >
      {children}
    </span>
  );
}

/** "no_show" reads as "no-show" on screen. */
export const statusLabel = (s: string) => s.replace(/_/g, "-");

export const statusTone = (s: string) =>
  ({ booked: "blue", completed: "green", cancelled: "slate", no_show: "red" })[s] ?? "slate";

export const AI_DISCLAIMER =
  "AI-generated decision support, not a diagnosis or medical advice. Requires clinician review. In an emergency call your local emergency number.";

export function AiDisclaimer() {
  return (
    <p className="rounded-[5px] border border-line bg-paper px-3.5 py-2.5 text-xs leading-relaxed text-slate-700">
      <strong className="font-semibold text-navy-900">AI-generated, requires clinician review.</strong>{" "}
      {AI_DISCLAIMER}
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
