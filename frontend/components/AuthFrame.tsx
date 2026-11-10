import Link from "next/link";
import { Wordmark } from "./Brand";
import { cx } from "./ui";

const EMERGENCY =
  "If you are having a medical emergency, call your local emergency number. This portal is not for emergencies.";

/** Signed-out pages: a navy panel on the left, the form on white. */
export function AuthFrame({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-white lg:grid lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      <aside className="relative overflow-hidden bg-navy-900 px-6 py-5 text-white lg:flex lg:flex-col lg:px-12 lg:py-12">
        <Link
          href="/login"
          className="inline-block rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-marigold-400 focus-visible:ring-offset-4 focus-visible:ring-offset-navy-900"
        >
          <Wordmark />
        </Link>
        <div className="relative z-10 mt-auto hidden max-w-sm lg:block">
          <p className="font-serif text-[2.6rem] font-medium leading-[1.1] tracking-[-0.015em]">
            Book visits, check symptoms and keep your records close.
          </p>
          <p className="mt-5 text-[15px] leading-relaxed text-navy-200">
            Reception, doctors and administrators sign in here too.
          </p>
          <p className="mt-10 border-l-2 border-marigold-400 pl-4 text-sm leading-relaxed text-navy-100">
            {EMERGENCY}
          </p>
        </div>
        {/* Oversized hospital cross, cropped by the panel edge. */}
        <svg
          aria-hidden="true"
          viewBox="0 0 100 100"
          className="pointer-events-none absolute -right-24 -top-24 hidden h-[30rem] w-[30rem] text-navy-800 lg:block"
        >
          <path
            d="M36 4h28v32h32v28H64v32H36V64H4V36h32z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.2"
          />
          <path d="M42 10h16v32h32v16H58v32H42V58H10V42h32z" fill="currentColor" opacity="0.55" />
        </svg>
      </aside>
      <main className="flex px-5 py-10 sm:px-8 lg:items-center lg:py-16">
        <div className="mx-auto w-full max-w-[26rem]">
          {children}
          <p className="mt-10 border-l-2 border-marigold-400 pl-3 text-xs leading-relaxed text-slate-600 lg:hidden">
            {EMERGENCY}
          </p>
        </div>
      </main>
    </div>
  );
}

/** Signed-in pages outside a role portal (MFA, change password). */
export function PlainFrame({ children, wide }: { children: React.ReactNode; wide?: boolean }) {
  return (
    <div className="min-h-screen">
      <header className="bg-navy-900 px-5 py-4">
        <div className={cx("mx-auto flex items-center justify-between", wide ? "max-w-lg" : "max-w-md")}>
          <Link
            href="/"
            className="rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-marigold-400 focus-visible:ring-offset-4 focus-visible:ring-offset-navy-900"
          >
            <Wordmark />
          </Link>
          {wide && (
            <Link
              href="/"
              className="text-sm text-navy-100 underline-offset-4 hover:text-white hover:underline"
            >
              Back to portal
            </Link>
          )}
        </div>
      </header>
      {children}
    </div>
  );
}
