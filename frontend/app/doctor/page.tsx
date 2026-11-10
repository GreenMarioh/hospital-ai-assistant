"use client";

import Link from "next/link";
import { useState } from "react";
import { Calendar, type Appt } from "@/components/Calendar";
import { Alert, Button, Card, ErrorState, Spinner, useAsync } from "@/components/ui";
import { api, errorMessage, unwrap } from "@/lib/api";
import { addDays, fmtDateTime, todayLocal, weekStart } from "@/lib/time";

export default function DoctorSchedule() {
  const [date, setDate] = useState(todayLocal());
  const [view, setView] = useState<"day" | "week">("day");
  const [sel, setSel] = useState<Appt | null>(null);
  const [msg, setMsg] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const from = view === "day" ? date : weekStart(date);
  const to = view === "day" ? date : addDays(weekStart(date), 6);
  const appts = useAsync(
    async () => unwrap(await api.GET("/api/appointments", { params: { query: { from, to } } })),
    [from, to],
  );

  async function outcome(kind: "complete" | "no-show", a: Appt) {
    const url =
      kind === "complete" ? "/api/appointments/{appt_id}/complete" : "/api/appointments/{appt_id}/no-show";
    const res = await api.POST(url, { params: { path: { appt_id: a.id } } });
    if (res.data) {
      setMsg({ kind: "success", text: `Marked ${res.data.status}.` });
      setSel(null);
      appts.reload();
    } else setMsg({ kind: "error", text: errorMessage(res.error) });
  }

  return (
    <>
      <h1 className="page-title">My schedule</h1>
      {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
      <Card>
        {appts.loading ? (
          <Spinner />
        ) : appts.error ? (
          <ErrorState error={appts.error} retry={appts.reload} />
        ) : (
          <Calendar
            appointments={appts.data ?? []}
            date={date}
            view={view}
            onDateChange={setDate}
            onViewChange={setView}
            onSelect={setSel}
          />
        )}
      </Card>
      {sel && (
        <Card title="Selected appointment">
          <p className="text-sm">
            <strong>{sel.patient_name}</strong> · {fmtDateTime(sel.starts_at)} · {sel.status}
          </p>
          {sel.reason && <p className="text-sm text-slate-700">Reason: {sel.reason}</p>}
          <div className="mt-3 flex flex-wrap gap-2">
            <Link
              className="inline-flex items-center rounded-[5px] bg-navy-800 px-3.5 py-2 text-sm font-medium text-white hover:bg-navy-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-navy-600 focus-visible:ring-offset-2"
              href={`/doctor/patients/${sel.patient_id}`}
            >
              Open chart &amp; AI briefing
            </Link>
            {sel.status === "booked" && (
              <>
                <Button variant="secondary" onClick={() => outcome("complete", sel)}>
                  Mark completed
                </Button>
                <Button variant="secondary" onClick={() => outcome("no-show", sel)}>
                  Mark no-show
                </Button>
              </>
            )}
          </div>
        </Card>
      )}
    </>
  );
}
