"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { Alert, Badge, Button, Card, Empty, ErrorState, Select, Spinner, useAsync } from "@/components/ui";
import { api, unwrap, uploadDocument } from "@/lib/api";
import { fmtDateTime } from "@/lib/time";

export default function ReceptionPatient() {
  const { id } = useParams<{ id: string }>();
  const [docType, setDocType] = useState("other");
  const [msg, setMsg] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const data = useAsync(async () => {
    const [p, docs, timeline] = await Promise.all([
      api.GET("/api/patients/{patient_id}", { params: { path: { patient_id: id } } }).then(unwrap),
      api.GET("/api/patients/{patient_id}/documents", { params: { path: { patient_id: id } } }).then(unwrap),
      api.GET("/api/patients/{patient_id}/timeline", { params: { path: { patient_id: id } } }).then(unwrap),
    ]);
    return { p, docs, timeline };
  }, [id]);
  if (data.loading && !data.data) return <Spinner />;
  if (data.error || !data.data) return <ErrorState error={data.error} retry={data.reload} />;
  const { p, docs, timeline } = data.data;
  return (
    <>
      <h1 className="page-title">
        {p.first_name} {p.last_name}
      </h1>
      <Card title="Demographics">
        <dl className="grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
          <div>
            <dt className="text-slate-600">Date of birth</dt>
            <dd>{p.date_of_birth}</dd>
          </div>
          <div>
            <dt className="text-slate-600">Phone</dt>
            <dd>{p.phone ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-600">Email</dt>
            <dd>{p.email ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-600">Blood group</dt>
            <dd>{p.blood_group ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-600">Allergies</dt>
            <dd>{p.allergies?.join(", ") || "None recorded"}</dd>
          </div>
          <div>
            <dt className="text-slate-600">Insurance</dt>
            <dd>
              {p.insurance_provider ?? "—"} {p.insurance_id_masked}
            </dd>
          </div>
          <div>
            <dt className="text-slate-600">Emergency contact</dt>
            <dd>
              {p.emergency_contact_name ?? "—"} {p.emergency_contact_phone}
            </dd>
          </div>
        </dl>
      </Card>
      <Card title="Documents">
        {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
        <form
          className="my-3 flex flex-wrap items-end gap-2"
          onSubmit={async (e) => {
            e.preventDefault();
            const input = e.currentTarget.elements.namedItem("file") as HTMLInputElement;
            const file = input.files?.[0];
            if (!file) return;
            try {
              await uploadDocument(id, file, docType);
              setMsg({ kind: "success", text: "Document uploaded." });
              input.value = "";
              data.reload();
            } catch (err) {
              setMsg({ kind: "error", text: (err as Error).message });
            }
          }}
        >
          <div>
            <label htmlFor="file" className="block text-[13px] font-medium text-navy-900">
              File (PDF, PNG or JPEG, max 10 MB)
            </label>
            <input
              id="file"
              name="file"
              type="file"
              accept="application/pdf,image/png,image/jpeg"
              required
              className="mt-1 text-sm"
            />
          </div>
          <Select label="Type" value={docType} onChange={(e) => setDocType(e.target.value)}>
            {["lab_report", "imaging", "referral", "insurance", "consent", "other"].map((t) => (
              <option key={t}>{t}</option>
            ))}
          </Select>
          <Button type="submit">Upload</Button>
        </form>
        {docs.length === 0 ? (
          <Empty>No documents.</Empty>
        ) : (
          <ul className="divide-y text-sm">
            {docs.map((d) => (
              <li key={d.id} className="py-2">
                {d.filename} <Badge>{d.doc_type}</Badge> · {fmtDateTime(d.created_at)}
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Card title="Timeline">
        {timeline.length === 0 ? (
          <Empty>No activity.</Empty>
        ) : (
          <ol className="space-y-1 text-sm">
            {timeline.map((e) => (
              <li key={`${e.kind}-${e.id}`}>
                {fmtDateTime(e.at)} · {e.title}
              </li>
            ))}
          </ol>
        )}
      </Card>
    </>
  );
}
