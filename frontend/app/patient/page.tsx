"use client";

import Link from "next/link";
import { Card, Empty, ErrorState, Spinner, useAsync, Badge, statusTone } from "@/components/ui";
import { api, unwrap } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtDateTime } from "@/lib/time";

export default function PatientHome() {
  const { user } = useAuth();
  const appts = useAsync(
    async () => unwrap(await api.GET("/api/appointments", { params: { query: { status: "booked" } } })),
    [],
  );
  const upcoming = (appts.data ?? []).filter((a) => new Date(a.starts_at) > new Date());
  return (
    <>
      <h1 className="text-2xl font-bold">Welcome, {user?.full_name}</h1>
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Not feeling well?">
          <p className="mb-3 text-sm text-slate-700">
            Describe your symptoms and we will suggest the right department.
          </p>
          <Link className="text-sm font-medium text-blue-800 underline" href="/patient/assistant">
            Start symptom check
          </Link>
        </Card>
        <Card title="Need an appointment?">
          <p className="mb-3 text-sm text-slate-700">Pick a doctor and time, or ask the booking assistant.</p>
          <Link className="text-sm font-medium text-blue-800 underline" href="/patient/book">
            Book now
          </Link>
        </Card>
      </div>
      <Card title="Upcoming appointments">
        {appts.loading ? (
          <Spinner />
        ) : appts.error ? (
          <ErrorState error={appts.error} retry={appts.reload} />
        ) : upcoming.length === 0 ? (
          <Empty>No upcoming appointments.</Empty>
        ) : (
          <ul className="divide-y">
            {upcoming.map((a) => (
              <li key={a.id} className="flex items-center justify-between py-2 text-sm">
                <span>
                  {fmtDateTime(a.starts_at)} with {a.doctor_name}
                </span>
                <Badge tone={statusTone(a.status)}>{a.status}</Badge>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
