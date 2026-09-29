"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import {
  AiDisclaimer,
  Alert,
  Badge,
  Button,
  Card,
  Empty,
  ErrorState,
  Field,
  Spinner,
  useAsync,
} from "@/components/ui";
import { api, errorMessage, unwrap, type Schemas } from "@/lib/api";
import { fmtDateTime } from "@/lib/time";

function Briefing({ patientId }: { patientId: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const saved = useAsync(
    async () =>
      unwrap(
        await api.GET("/api/ai/patients/{patient_id}/summaries", {
          params: { path: { patient_id: patientId } },
        }),
      ),
    [patientId],
  );
  const [fresh, setFresh] = useState<Schemas["BriefingOut"] | null>(null);
  const b = fresh ?? saved.data?.find((s) => s.kind === "briefing") ?? null;
  return (
    <Card
      title="Pre-visit AI briefing"
      actions={
        <Button
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setError(null);
            const res = await api.POST("/api/ai/patients/{patient_id}/briefing", {
              params: { path: { patient_id: patientId } },
            });
            setBusy(false);
            if (res.data) {
              setFresh(res.data);
              saved.reload();
            } else setError(errorMessage(res.error));
          }}
        >
          {busy ? "Generating…" : b ? "Regenerate briefing" : "Generate briefing"}
        </Button>
      }
    >
      <div aria-live="polite" className="space-y-3 text-sm">
        <AiDisclaimer />
        {error && <Alert kind="error">{error}</Alert>}
        {b ? (
          <>
            {!b.ai_generated && (
              <Alert kind="warning">
                AI service unavailable: showing a structured overview from the record only.
              </Alert>
            )}
            <p>{b.summary}</p>
            {b.flags.length > 0 && (
              <div>
                <h3 className="font-semibold">Flagged items</h3>
                <ul className="list-disc pl-5">
                  {b.flags.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              </div>
            )}
            {b.key_history.length > 0 && (
              <div>
                <h3 className="font-semibold">Key history</h3>
                <ul className="list-disc pl-5">
                  {b.key_history.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              </div>
            )}
            {b.recent_visits.length > 0 && (
              <div>
                <h3 className="font-semibold">Recent visits</h3>
                <ul className="list-disc pl-5">
                  {b.recent_visits.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-xs text-slate-600">Generated {fmtDateTime(b.created_at)}</p>
          </>
        ) : (
          <Empty>No briefing yet. Generate one before the visit.</Empty>
        )}
      </div>
    </Card>
  );
}

function VisitForm({ patientId, done }: { patientId: string; done: () => void }) {
  const [f, setF] = useState({
    chief_complaint: "",
    notes: "",
    diagnosis: "",
    follow_up_date: "",
    heart_rate: "",
    spo2: "",
    drug: "",
    dosage: "",
  });
  const [msg, setMsg] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setF({ ...f, [k]: e.target.value });
  return (
    <Card title="Add visit note">
      <form
        className="space-y-3"
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            const visit = unwrap(
              await api.POST("/api/patients/{patient_id}/visits", {
                params: { path: { patient_id: patientId } },
                body: {
                  chief_complaint: f.chief_complaint || null,
                  notes: f.notes || null,
                  diagnosis: f.diagnosis || null,
                  follow_up_date: f.follow_up_date || null,
                  vitals: {
                    ...(f.heart_rate ? { heart_rate: Number(f.heart_rate) } : {}),
                    ...(f.spo2 ? { spo2: Number(f.spo2) } : {}),
                  },
                },
              }),
            );
            if (f.drug) {
              unwrap(
                await api.POST("/api/visits/{visit_id}/prescriptions", {
                  params: { path: { visit_id: visit.id } },
                  body: { drug_name: f.drug, dosage: f.dosage || null },
                }),
              );
            }
            setMsg({ kind: "success", text: "Visit note saved." });
            setF({
              chief_complaint: "",
              notes: "",
              diagnosis: "",
              follow_up_date: "",
              heart_rate: "",
              spo2: "",
              drug: "",
              dosage: "",
            });
            done();
          } catch (err) {
            setMsg({ kind: "error", text: (err as Error).message });
          }
        }}
      >
        {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
        <Field label="Chief complaint" value={f.chief_complaint} onChange={set("chief_complaint")} />
        <div>
          <label htmlFor="notes" className="block text-sm font-medium">
            Notes
          </label>
          <textarea
            id="notes"
            rows={4}
            value={f.notes}
            onChange={set("notes")}
            className="mt-1 w-full rounded border border-slate-500 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
          />
        </div>
        <Field label="Diagnosis (clinician-entered)" value={f.diagnosis} onChange={set("diagnosis")} />
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Field
            label="Heart rate"
            type="number"
            min={20}
            max={300}
            value={f.heart_rate}
            onChange={set("heart_rate")}
          />
          <Field label="SpO2 %" type="number" min={30} max={100} value={f.spo2} onChange={set("spo2")} />
          <Field label="Prescription drug" value={f.drug} onChange={set("drug")} />
          <Field label="Dosage" value={f.dosage} onChange={set("dosage")} />
        </div>
        <Field
          label="Follow-up date"
          type="date"
          value={f.follow_up_date}
          onChange={set("follow_up_date")}
          className="max-w-xs"
        />
        <Button type="submit">Save visit note</Button>
      </form>
    </Card>
  );
}

export default function DoctorChart() {
  const { id } = useParams<{ id: string }>();
  const data = useAsync(async () => {
    const [p, visits, timeline] = await Promise.all([
      api.GET("/api/patients/{patient_id}", { params: { path: { patient_id: id } } }).then(unwrap),
      api.GET("/api/patients/{patient_id}/visits", { params: { path: { patient_id: id } } }).then(unwrap),
      api.GET("/api/patients/{patient_id}/timeline", { params: { path: { patient_id: id } } }).then(unwrap),
    ]);
    return { p, visits, timeline };
  }, [id]);
  if (data.loading && !data.data) return <Spinner />;
  if (data.error || !data.data) return <ErrorState error={data.error} retry={data.reload} />;
  const { p, visits, timeline } = data.data;
  return (
    <>
      <h1 className="text-2xl font-bold">
        {p.first_name} {p.last_name}
      </h1>
      <p className="text-sm text-slate-700">
        DOB {p.date_of_birth} · Blood group {p.blood_group ?? "—"} · Allergies:{" "}
        {p.allergies?.join(", ") || "none recorded"}
      </p>
      <Briefing patientId={id} />
      <VisitForm patientId={id} done={data.reload} />
      <Card title="Visits">
        {visits.length === 0 ? (
          <Empty>No visits recorded.</Empty>
        ) : (
          <ul className="divide-y text-sm">
            {visits.map((v) => (
              <li key={v.id} className="py-2">
                <p className="font-medium">
                  {fmtDateTime(v.created_at)} — {v.chief_complaint ?? "Visit"} <Badge>v{v.version}</Badge>
                </p>
                {v.notes && <p className="whitespace-pre-wrap">{v.notes}</p>}
                {v.diagnosis && <p>Diagnosis: {v.diagnosis}</p>}
                {v.prescriptions.length > 0 && (
                  <p>
                    Prescriptions: {v.prescriptions.map((r) => `${r.drug_name} ${r.dosage ?? ""}`).join(", ")}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Card title="Timeline">
        <ol className="space-y-1 text-sm">
          {timeline.map((e) => (
            <li key={`${e.kind}-${e.id}`}>
              {fmtDateTime(e.at)} · {e.title}
            </li>
          ))}
        </ol>
      </Card>
    </>
  );
}
