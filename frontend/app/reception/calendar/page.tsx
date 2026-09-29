"use client";

import { useState } from "react";
import { Calendar, type Appt } from "@/components/Calendar";
import { Alert, Button, Card, Select, Spinner, ErrorState, Field, useAsync } from "@/components/ui";
import { api, errorMessage, unwrap } from "@/lib/api";
import { addDays, fmtDateTime, fmtTime, localDate, todayLocal, weekStart } from "@/lib/time";

export default function ReceptionCalendar() {
  const [doctorId, setDoctorId] = useState("");
  const [date, setDate] = useState(todayLocal());
  const [view, setView] = useState<"day" | "week">("week");
  const [sel, setSel] = useState<Appt | null>(null);
  const [msg, setMsg] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [patientQ, setPatientQ] = useState("");
  const [patientId, setPatientId] = useState("");

  const doctors = useAsync(async () => unwrap(await api.GET("/api/doctors")), []);
  const from = view === "day" ? date : weekStart(date);
  const to = view === "day" ? date : addDays(weekStart(date), 6);
  const appts = useAsync(async () => {
    if (!doctorId) return [];
    return unwrap(
      await api.GET("/api/appointments", { params: { query: { doctor_id: doctorId, from, to } } }),
    );
  }, [doctorId, from, to]);
  const slots = useAsync(async () => {
    if (!doctorId) return [];
    return unwrap(
      await api.GET("/api/doctors/{doctor_id}/slots", {
        params: { path: { doctor_id: doctorId }, query: { from: date, to: date } },
      }),
    );
  }, [doctorId, date]);
  const found = useAsync(
    async () =>
      patientQ.length < 2
        ? null
        : unwrap(await api.GET("/api/patients", { params: { query: { q: patientQ, size: 5 } } })),
    [patientQ],
  );

  async function act(path: "cancel" | "no-show", a: Appt) {
    const url =
      path === "cancel" ? "/api/appointments/{appt_id}/cancel" : "/api/appointments/{appt_id}/no-show";
    const res = await api.POST(url, { params: { path: { appt_id: a.id } } });
    if (res.data) {
      setMsg({ kind: "success", text: `Appointment ${res.data.status}.` });
      setSel(null);
      appts.reload();
      slots.reload();
    } else setMsg({ kind: "error", text: errorMessage(res.error) });
  }

  async function book(start: string) {
    const res = await api.POST("/api/appointments", {
      body: { doctor_id: doctorId, patient_id: patientId, starts_at: start },
    });
    if (res.data) {
      setMsg({ kind: "success", text: `Booked ${fmtDateTime(res.data.starts_at)}.` });
      appts.reload();
      slots.reload();
    } else setMsg({ kind: "error", text: errorMessage(res.error) });
  }

  return (
    <>
      <h1 className="text-2xl font-bold">Calendar &amp; booking</h1>
      <Card>
        <Select
          label="Doctor"
          value={doctorId}
          onChange={(e) => setDoctorId(e.target.value)}
          className="max-w-sm"
        >
          <option value="">Select a doctor…</option>
          {doctors.data?.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name} ({d.department})
            </option>
          ))}
        </Select>
      </Card>
      {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
      {doctorId && (
        <>
          <Card title="Schedule">
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
            {sel && (
              <div
                className="mt-3 rounded border border-slate-300 p-3 text-sm"
                role="region"
                aria-label="Selected appointment"
              >
                <p>
                  <strong>{sel.patient_name}</strong> · {fmtDateTime(sel.starts_at)} · {sel.status}
                </p>
                {sel.status === "booked" && (
                  <div className="mt-2 flex gap-2">
                    <Button variant="danger" onClick={() => act("cancel", sel)}>
                      Cancel appointment
                    </Button>
                    <Button variant="secondary" onClick={() => act("no-show", sel)}>
                      Mark no-show
                    </Button>
                  </div>
                )}
              </div>
            )}
          </Card>
          <Card title={`Book on ${date}`}>
            <Field
              label="Find patient (name, phone)"
              value={patientQ}
              onChange={(e) => setPatientQ(e.target.value)}
              className="max-w-sm"
            />
            {found.data && (
              <Select
                label="Patient"
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
                className="mt-2 max-w-sm"
              >
                <option value="">Select…</option>
                {found.data.items.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.first_name} {p.last_name} · {p.date_of_birth}
                  </option>
                ))}
              </Select>
            )}
            <div className="mt-3 flex flex-wrap gap-2">
              {(slots.data ?? [])
                .filter((s) => localDate(s.starts_at) === date)
                .map((s) => (
                  <Button
                    key={s.starts_at}
                    variant="secondary"
                    disabled={!patientId}
                    onClick={() => book(s.starts_at)}
                  >
                    {fmtTime(s.starts_at)}
                  </Button>
                ))}
              {!slots.loading && (slots.data ?? []).length === 0 && (
                <p className="text-sm text-slate-600">No free slots this day.</p>
              )}
            </div>
          </Card>
        </>
      )}
    </>
  );
}
