"use client";

import { Badge, Card, Empty, ErrorState, Spinner, useAsync } from "@/components/ui";
import { api, download, unwrap } from "@/lib/api";
import { fmtDateTime } from "@/lib/time";

export default function RecordsPage() {
  const data = useAsync(async () => {
    const me = unwrap(await api.GET("/api/patients/me"));
    const [visits, docs, timeline] = await Promise.all([
      api.GET("/api/patients/{patient_id}/visits", { params: { path: { patient_id: me.id } } }).then(unwrap),
      api
        .GET("/api/patients/{patient_id}/documents", { params: { path: { patient_id: me.id } } })
        .then(unwrap),
      api
        .GET("/api/patients/{patient_id}/timeline", { params: { path: { patient_id: me.id } } })
        .then(unwrap),
    ]);
    return { me, visits, docs, timeline };
  }, []);

  if (data.loading && !data.data) return <Spinner />;
  if (data.error || !data.data) return <ErrorState error={data.error} retry={data.reload} />;
  const { me, visits, docs, timeline } = data.data;
  return (
    <>
      <h1 className="text-2xl font-bold">My records</h1>
      <Card title="Profile">
        <dl className="grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
          <div>
            <dt className="text-slate-600">Name</dt>
            <dd>
              {me.first_name} {me.last_name}
            </dd>
          </div>
          <div>
            <dt className="text-slate-600">Date of birth</dt>
            <dd>{me.date_of_birth}</dd>
          </div>
          <div>
            <dt className="text-slate-600">Blood group</dt>
            <dd>{me.blood_group ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-600">Allergies</dt>
            <dd>{me.allergies?.length ? me.allergies.join(", ") : "None recorded"}</dd>
          </div>
        </dl>
      </Card>
      <Card title="Visits">
        {visits.length === 0 ? (
          <Empty>No visits recorded.</Empty>
        ) : (
          <ul className="divide-y text-sm">
            {visits.map((v) => (
              <li key={v.id} className="py-2">
                <p className="font-medium">
                  {fmtDateTime(v.created_at)} — {v.chief_complaint ?? "Visit"}
                </p>
                {v.diagnosis && <p>Diagnosis: {v.diagnosis}</p>}
                {v.prescriptions.length > 0 && (
                  <p>
                    Prescriptions: {v.prescriptions.map((p) => `${p.drug_name} ${p.dosage ?? ""}`).join(", ")}
                  </p>
                )}
                {v.follow_up_date && <p>Follow-up: {v.follow_up_date}</p>}
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Card title="Documents">
        {docs.length === 0 ? (
          <Empty>No documents on file.</Empty>
        ) : (
          <ul className="divide-y text-sm">
            {docs.map((d) => (
              <li key={d.id} className="flex items-center justify-between py-2">
                <span>
                  {d.filename} <Badge>{d.doc_type}</Badge>
                </span>
                <button
                  className="text-blue-800 underline"
                  onClick={async () => {
                    const link = unwrap(
                      await api.GET("/api/documents/{doc_id}/link", { params: { path: { doc_id: d.id } } }),
                    );
                    window.open(
                      `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}${link.url}`,
                      "_blank",
                      "noopener",
                    );
                  }}
                >
                  Download
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Card title="Timeline">
        {timeline.length === 0 ? (
          <Empty>Nothing yet.</Empty>
        ) : (
          <ol className="space-y-1 text-sm">
            {timeline.map((e) => (
              <li key={`${e.kind}-${e.id}`}>
                {fmtDateTime(e.at)} · <span className="text-slate-700">{e.title}</span>
              </li>
            ))}
          </ol>
        )}
      </Card>
    </>
  );
}
