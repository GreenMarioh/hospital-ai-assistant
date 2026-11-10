"use client";

import Link from "next/link";
import { Badge, Card, Empty, ErrorState, Spinner, statusLabel, statusTone, useAsync } from "@/components/ui";
import { api, unwrap } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtDateTime } from "@/lib/time";

const actionLink =
  "inline-flex items-center rounded-[5px] px-3.5 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-navy-600 focus-visible:ring-offset-2";

export default function PatientHome() {
  const { user } = useAuth();
  const appts = useAsync(
    async () => unwrap(await api.GET("/api/appointments", { params: { query: { status: "booked" } } })),
    [],
  );
  const upcoming = (appts.data ?? [])
    .filter((a) => new Date(a.starts_at) > new Date())
    .sort((a, b) => a.starts_at.localeCompare(b.starts_at));
  const next = upcoming[0];
  return (
    <>
      <div>
        <h1 className="page-title">Welcome, {user?.full_name}</h1>
        <p className="mt-2 text-[15px] text-slate-600">
          {appts.loading || appts.error
            ? "What would you like to do today?"
            : next
              ? `Your next visit is ${fmtDateTime(next.starts_at)} with ${next.doctor_name}.`
              : "You have no visits booked."}
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <section className="flex flex-col rounded-lg bg-navy-900 p-6 text-white">
          <h2 className="font-serif text-xl font-semibold text-white">Not feeling well?</h2>
          <p className="mb-5 mt-2 max-w-sm text-sm leading-relaxed text-navy-100">
            Describe your symptoms and we will suggest the right department.
          </p>
          <Link
            className={`${actionLink} mt-auto self-start bg-marigold-400 text-navy-950 hover:bg-marigold-300 focus-visible:ring-marigold-400 focus-visible:ring-offset-navy-900`}
            href="/patient/assistant"
          >
            Start symptom check
          </Link>
        </section>
        <section className="flex flex-col rounded-lg border border-line bg-white p-6">
          <h2 className="font-serif text-xl font-semibold">Need an appointment?</h2>
          <p className="mb-5 mt-2 max-w-sm text-sm leading-relaxed text-slate-600">
            Pick a doctor and time, or ask the booking assistant.
          </p>
          <Link
            className={`${actionLink} mt-auto self-start bg-navy-800 text-white hover:bg-navy-900`}
            href="/patient/book"
          >
            Book now
          </Link>
        </section>
      </div>
      <Card
        title="Upcoming appointments"
        actions={
          upcoming.length > 0 && (
            <Link href="/patient/appointments" className="link text-sm">
              Manage appointments
            </Link>
          )
        }
      >
        {appts.loading ? (
          <Spinner />
        ) : appts.error ? (
          <ErrorState error={appts.error} retry={appts.reload} />
        ) : upcoming.length === 0 ? (
          <Empty>No upcoming appointments.</Empty>
        ) : (
          <ul className="divide-y divide-line">
            {upcoming.map((a) => (
              <li key={a.id} className="flex items-center justify-between gap-3 py-3 text-sm">
                <span>
                  <span className="num block font-semibold text-navy-900">{fmtDateTime(a.starts_at)}</span>
                  <span className="text-slate-600">with {a.doctor_name}</span>
                </span>
                <Badge tone={statusTone(a.status)}>{statusLabel(a.status)}</Badge>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
