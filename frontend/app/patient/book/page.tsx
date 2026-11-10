"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ChatInput, ChatLog, type ChatMsg } from "@/components/Chat";
import { Alert, Button, Card, Empty, ErrorState, Field, Select, Spinner, useAsync } from "@/components/ui";
import { api, errorMessage, unwrap, type Schemas } from "@/lib/api";
import { addDays, fmtDateTime, fmtTime, localDate, todayLocal, weekdayLabel } from "@/lib/time";

function Waitlist({ doctorId }: { doctorId: string }) {
  const [date, setDate] = useState(addDays(todayLocal(), 1));
  const [msg, setMsg] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  return (
    <div className="mt-5 rounded-md bg-paper p-4" role="group" aria-label="Join waitlist">
      <p className="text-sm font-medium">Preferred day is full? Join the waitlist.</p>
      <p className="text-xs text-slate-600">We will email or text you if a slot opens on that day.</p>
      {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
      <form
        className="mt-2 flex flex-wrap items-end gap-2"
        onSubmit={async (e) => {
          e.preventDefault();
          const res = await api.POST("/api/waitlist", { body: { doctor_id: doctorId, desired_date: date } });
          setMsg(
            res.data
              ? { kind: "success", text: `You are on the waitlist for ${date}.` }
              : { kind: "error", text: errorMessage(res.error) },
          );
        }}
      >
        <Field
          label="Date"
          type="date"
          min={todayLocal()}
          value={date}
          onChange={(e) => setDate(e.target.value)}
          required
        />
        <Button type="submit" variant="secondary">
          Join waitlist
        </Button>
      </form>
    </div>
  );
}

function ManualBooking() {
  const router = useRouter();
  const [dept, setDept] = useState("");
  const [doctorId, setDoctorId] = useState("");
  const [reason, setReason] = useState("");
  const [msg, setMsg] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [booking, setBooking] = useState<string | null>(null);

  const depts = useAsync(async () => unwrap(await api.GET("/api/departments")), []);
  const doctors = useAsync(
    async () =>
      unwrap(
        await api.GET("/api/doctors", { params: { query: dept ? { department_id: Number(dept) } : {} } }),
      ),
    [dept],
  );
  const slots = useAsync(async () => {
    if (!doctorId) return [];
    const from = todayLocal();
    return unwrap(
      await api.GET("/api/doctors/{doctor_id}/slots", {
        params: { path: { doctor_id: doctorId }, query: { from, to: addDays(from, 13) } },
      }),
    );
  }, [doctorId]);

  const byDay = new Map<string, Schemas["SlotOut"][]>();
  for (const s of slots.data ?? []) {
    const d = localDate(s.starts_at);
    byDay.set(d, [...(byDay.get(d) ?? []), s]);
  }

  async function book(start: string) {
    setBooking(start);
    setMsg(null);
    const res = await api.POST("/api/appointments", {
      body: { doctor_id: doctorId, starts_at: start, reason: reason || null },
      params: { header: { "idempotency-key": crypto.randomUUID() } },
    });
    setBooking(null);
    if (res.data) {
      setMsg({ kind: "success", text: `Booked for ${fmtDateTime(res.data.starts_at)}.` });
      slots.reload();
      setTimeout(() => router.push("/patient/appointments"), 1200);
    } else {
      setMsg({ kind: "error", text: errorMessage(res.error) });
      slots.reload();
    }
  }

  return (
    <Card title="Choose a doctor and time">
      <div className="grid gap-3 md:grid-cols-2">
        <Select
          label="Department"
          value={dept}
          onChange={(e) => {
            setDept(e.target.value);
            setDoctorId("");
          }}
        >
          <option value="">All departments</option>
          {depts.data?.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </Select>
        <Select label="Doctor" value={doctorId} onChange={(e) => setDoctorId(e.target.value)}>
          <option value="">Select a doctor…</option>
          {doctors.data?.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name} ({d.department})
            </option>
          ))}
        </Select>
      </div>
      <div className="mt-3">
        <label htmlFor="reason" className="block text-[13px] font-medium text-navy-900">
          Reason for visit (optional)
        </label>
        <input
          id="reason"
          maxLength={1000}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="mt-1.5 w-full rounded-[5px] border border-slate-400 bg-white px-3 py-2 text-sm hover:border-navy-400 focus:border-navy-700 focus:outline-none focus:ring-2 focus:ring-navy-100"
        />
      </div>
      {msg && (
        <div className="mt-3">
          <Alert kind={msg.kind}>{msg.text}</Alert>
        </div>
      )}
      <div className="mt-4">
        {!doctorId ? (
          <Empty>Select a doctor to see available times.</Empty>
        ) : slots.loading ? (
          <Spinner label="Loading times" />
        ) : slots.error ? (
          <ErrorState error={slots.error} retry={slots.reload} />
        ) : byDay.size === 0 ? (
          <Empty>No free slots in the next two weeks.</Empty>
        ) : (
          [...byDay.entries()].slice(0, 7).map(([day, list]) => (
            <div key={day} className="mb-4">
              <h3 className="text-[13px] font-semibold text-navy-900">{weekdayLabel(day)}</h3>
              <div className="mt-1 flex flex-wrap gap-2">
                {list.slice(0, 16).map((s) => (
                  <Button
                    key={s.starts_at}
                    variant="secondary"
                    disabled={booking !== null}
                    aria-label={`Book ${weekdayLabel(day)} at ${fmtTime(s.starts_at)}`}
                    onClick={() => book(s.starts_at)}
                  >
                    {fmtTime(s.starts_at)}
                  </Button>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}

function BookingAssistant() {
  const router = useRouter();
  const [msgs, setMsgs] = useState<ChatMsg[]>([]);
  const [conv, setConv] = useState<string | undefined>();
  const [proposal, setProposal] = useState<Schemas["BookingProposal"] | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<{ kind: "error" | "success" | "warning"; text: string } | null>(null);
  const status = useAsync(async () => unwrap(await api.GET("/api/ai/status")), []);

  async function send(text: string) {
    setMsgs((m) => [...m, { role: "user", text }]);
    setBusy(true);
    setNote(null);
    setProposal(null);
    const res = await api.POST("/api/ai/booking/message", { body: { message: text, conversation_id: conv } });
    setBusy(false);
    if (!res.data) {
      setNote({ kind: res.response.status === 503 ? "warning" : "error", text: errorMessage(res.error) });
      return;
    }
    setConv(res.data.conversation_id);
    setMsgs((m) => [...m, { role: "assistant", text: res.data!.reply }]);
    setProposal(res.data.proposal ?? null);
  }

  async function confirm() {
    if (!proposal || !conv) return;
    setBusy(true);
    const res = await api.POST("/api/ai/booking/confirm", {
      body: { conversation_id: conv, proposal_id: proposal.proposal_id },
    });
    setBusy(false);
    if (res.data) {
      setNote({ kind: "success", text: `Booked for ${fmtDateTime(res.data.starts_at)}.` });
      setProposal(null);
      setTimeout(() => router.push("/patient/appointments"), 1200);
    } else setNote({ kind: "error", text: errorMessage(res.error) });
  }

  return (
    <Card title="Booking assistant">
      <div className="space-y-3">
        {status.data && !status.data.available && (
          <Alert kind="warning">The booking assistant is unavailable. Use the form above to book.</Alert>
        )}
        <p className="text-xs text-slate-600">
          Example: “book me a cardiologist next Tuesday morning”. Nothing is booked until you confirm.
        </p>
        {note && <Alert kind={note.kind}>{note.text}</Alert>}
        <ChatLog messages={msgs} busy={busy} />
        {proposal && (
          <div
            className="rounded-md border border-navy-700 bg-navy-50 p-4 text-sm"
            role="group"
            aria-label="Confirm booking"
          >
            <p className="font-semibold">Confirm this appointment?</p>
            <p>
              {proposal.doctor_name} · {fmtDateTime(proposal.starts_at)}
            </p>
            <div className="mt-2 flex gap-2">
              <Button onClick={confirm} disabled={busy}>
                Confirm booking
              </Button>
              <Button variant="secondary" onClick={() => setProposal(null)}>
                Not now
              </Button>
            </div>
          </div>
        )}
        <ChatInput
          onSend={send}
          disabled={busy || status.data?.available === false}
          label="Tell me who you'd like to see and when"
        />
      </div>
    </Card>
  );
}

export default function BookPage() {
  useEffect(() => {
    document.title = "Book appointment";
  }, []);
  return (
    <>
      <h1 className="page-title">Book an appointment</h1>
      <ManualBooking />
      <BookingAssistant />
    </>
  );
}
