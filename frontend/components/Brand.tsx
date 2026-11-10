import { cx } from "./ui";

/** The hospital cross: a plain Greek cross set in a rounded square. */
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={cx("shrink-0", className)}>
      <rect width="32" height="32" rx="7" fill="currentColor" />
      <path d="M13 7h6v6h6v6h-6v6h-6v-6H7v-6h6z" className="fill-navy-900" />
    </svg>
  );
}

export function Wordmark({ sub, tone = "light" }: { sub?: string; tone?: "light" | "dark" }) {
  return (
    <div className="flex items-center gap-2.5">
      <BrandMark className="h-8 w-8 text-marigold-400" />
      <div className="leading-tight">
        <p
          className={cx(
            "font-serif text-[17px] font-semibold tracking-[-0.01em]",
            tone === "light" ? "text-white" : "text-navy-900",
          )}
        >
          Hospital Assistant
        </p>
        {sub && <p className={cx("text-xs", tone === "light" ? "text-navy-200" : "text-slate-600")}>{sub}</p>}
      </div>
    </div>
  );
}
