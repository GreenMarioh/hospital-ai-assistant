"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { HOME, type Role } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Wordmark } from "./Brand";
import { Spinner, cx } from "./ui";

export type NavItem = { href: string; label: string };

/** Client-side route guard + layout. The API enforces RBAC independently; this only steers the UI. */
export function RoleShell({
  role,
  title,
  nav,
  children,
}: {
  role: Role;
  title: string;
  nav: NavItem[];
  children: React.ReactNode;
}) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const path = usePathname();

  useEffect(() => {
    if (loading) return;
    if (!user) router.replace("/login");
    else if (user.role !== role) router.replace(HOME[user.role]);
  }, [user, loading, role, router]);

  if (loading || !user || user.role !== role) return <Spinner label="Checking your session" />;

  const signOut = async () => {
    await logout();
    router.replace("/login");
  };

  const initials = user.full_name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join("");
  const focusDark =
    "focus:outline-none focus-visible:ring-2 focus-visible:ring-marigold-400 focus-visible:ring-offset-2 focus-visible:ring-offset-navy-900";

  return (
    <div className="min-h-screen md:flex">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:p-2 focus:text-navy-900"
      >
        Skip to content
      </a>
      <aside className="bg-navy-900 text-white md:sticky md:top-0 md:flex md:h-screen md:w-64 md:shrink-0 md:flex-col">
        <div className="flex items-center justify-between px-4 py-4 md:px-5 md:py-6">
          <Wordmark sub={title} />
          <button
            type="button"
            onClick={signOut}
            className={cx(
              "rounded-[5px] border border-navy-600 px-3 py-1.5 text-sm font-medium text-white hover:border-navy-400 hover:bg-navy-800 md:hidden",
              focusDark,
            )}
          >
            Sign out
          </button>
        </div>
        <nav
          aria-label={`${title} navigation`}
          className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-1 md:flex-col md:gap-0.5 md:overflow-visible md:pb-0"
        >
          {nav.map((n) => {
            const active = path === n.href || (n.href !== HOME[role] && path.startsWith(n.href));
            return (
              <Link
                key={n.href}
                href={n.href}
                aria-current={active ? "page" : undefined}
                className={cx(
                  "relative whitespace-nowrap rounded-[5px] px-3 py-2 text-sm transition-colors",
                  focusDark,
                  active
                    ? "bg-navy-800 font-semibold text-white before:absolute before:bottom-0 before:left-3 before:right-3 before:h-0.5 before:rounded-full before:bg-marigold-400 md:before:bottom-2 md:before:left-0 md:before:right-auto md:before:top-2 md:before:h-auto md:before:w-[3px]"
                    : "text-navy-100 hover:bg-navy-800/60 hover:text-white",
                )}
              >
                {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="hidden border-t border-navy-700 p-4 md:block">
          <div className="flex items-center gap-3">
            <span
              aria-hidden="true"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-navy-700 text-xs font-semibold text-navy-50"
            >
              {initials}
            </span>
            <p className="min-w-0 truncate text-sm font-medium text-white">{user.full_name}</p>
          </div>
          <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs">
            <Link href="/mfa" className={cx("text-navy-200 hover:text-white hover:underline", focusDark)}>
              Two-factor auth (MFA)
            </Link>
            <Link
              href="/change-password"
              className={cx("text-navy-200 hover:text-white hover:underline", focusDark)}
            >
              Change password
            </Link>
          </div>
          <button
            type="button"
            onClick={signOut}
            className={cx(
              "mt-4 w-full rounded-[5px] border border-navy-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:border-navy-400 hover:bg-navy-800",
              focusDark,
            )}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main id="main" className="min-w-0 flex-1">
        <div className="mx-auto max-w-6xl space-y-5 px-4 py-6 md:px-10 md:py-10">{children}</div>
        <div className="flex gap-4 px-4 pb-6 text-xs md:hidden">
          <Link href="/mfa" className="link">
            Two-factor auth (MFA)
          </Link>
          <Link href="/change-password" className="link">
            Change password
          </Link>
        </div>
      </main>
    </div>
  );
}
