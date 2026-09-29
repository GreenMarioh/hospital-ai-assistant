"use client";

import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Empty,
  ErrorState,
  Spinner,
  statusTone,
  useAsync,
} from "@/components/ui";
import { api, errorMessage, unwrap, type Schemas } from "@/lib/api";
import { addDays, fmtDateTime, localDate, todayLocal } from "@/lib/time";

function Reschedule({ appt, done }: { appt: Schemas["AppointmentOut"]; done: () => void }) {
  const [err, setErr] = useState<string | null>(null);
  const slots = useAsync(async () => {
    const from = todayLocal();
    return unwrap(
      await api.GET("/api/doctors/{doctor_id}/slots", {
        params: { path: { doctor_id: appt.doctor_id }, query: { from, to: addDays(from, 13) } },
      }),
    );
  }, [appt.doctor_id]);
  return (
    <div className="mt-2 rounded border border-slate-300 p-2">
      <p className="text-xs font-medium">Pick a new time</p>
      {err && <Alert kind="error">{err}</Alert>}
      {slots.loading ? (
        <Spinner />
      ) : slots.error ? (
        <ErrorState error={slots.error} />
      ) : (
        <div className="mt-1 flex max-h-40 flex-wrap gap-1 overflow-y-auto">
          {(slots.data ?? []).slice(0, 30).map((s) => (
            <Button
              key={s.starts_at}
              variant="secondary"
              className="!px-2 !py-1 text-xs"
              onClick={async () => {
                const res = await api.POST("/api/appointments/{appt_id}/reschedule", {
                  params: { path: { appt_id: appt.id } },
                  body: { starts_at: s.starts_at },
                });
                if (res.data) done();
                else setErr(errorMessage(res.error));
              }}
            >
              {localDate(s.starts_at).slice(5)} {fmtDateTime(s.starts_at).split(", ")[1]}
            </Button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function MyAppointments() {
  const appts = useAsync(async () => unwrap(await api.GET("/api/appointments")), []);
  const [msg, setMsg] = useState<string | null>(null);
  const [resched, setResched] = useState<string | null>(null);
  return (
    <>
      <h1 className="text-2xl font-bold">My appointments</h1>
      {msg && <Alert kind="error">{msg}</Alert>}
      <Card>
        {appts.loading ? (
          <Spinner />
        ) : appts.error ? (
          <ErrorState error={appts.error} retry={appts.reload} />
        ) : (appts.data ?? []).length === 0 ? (
          <Empty>You have no appointments yet.</Empty>
        ) : (
          <ul className="divide-y">
            {[...(appts.data ?? [])].reverse().map((a) => (
              <li key={a.id} className="py-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span>
                    {fmtDateTime(a.starts_at)} · {a.doctor_name}
                  </span>
                  <span className="flex items-center gap-2">
                    <Badge tone={statusTone(a.status)}>{a.status}</Badge>
                    {a.status === "booked" && new Date(a.starts_at) > new Date() && (
                      <>
                        <Button
                          variant="secondary"
                          onClick={() => setResched(resched === a.id ? null : a.id)}
                        >
                          Reschedule
                        </Button>
                        <Button
                          variant="danger"
                          onClick={async () => {
                            const res = await api.POST("/api/appointments/{appt_id}/cancel", {
                              params: { path: { appt_id: a.id } },
                            });
                            if (!res.data) setMsg(errorMessage(res.error));
                            else {
                              setMsg(null);
                              appts.reload();
                            }
                          }}
                        >
                          Cancel
                        </Button>
                      </>
                    )}
                  </span>
                </div>
                {resched === a.id && (
                  <Reschedule
                    appt={a}
                    done={() => {
                      setResched(null);
                      appts.reload();
                    }}
                  />
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
